"""
Filtre faceless v2 — partie B : visages sur les miniatures.

Pour une chaîne, on analyse ~6 miniatures de ses vidéos :
  1. YuNet (OpenCV) détecte les visages ; seuls les GRANDS visages comptent.
  2. SFace (OpenCV) calcule une empreinte de chaque visage.
  3. On compare les empreintes entre miniatures de la même chaîne.

Deux chiffres en sortie :
  face_ratio      = part des miniatures avec un grand visage
  same_face_ratio = part des miniatures montrant LA MÊME personne
                    (un créateur qui se montre : élevé ; une chaîne d'histoire
                    avec des portraits différents : faible)

Ces fonctions ne coûtent aucun quota YouTube (simples images publiques).
Elles tournent en local ou sur GitHub Actions, jamais sur Render.

Test rapide :
    python -m discovery.face_detect VIDEO_ID1 VIDEO_ID2 ...
    python -m discovery.face_detect --image miniature1.jpg miniature2.jpg
"""

import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
import requests

from config.face_settings import (
    DETECTOR_SCORE_THRESHOLD, DOWNLOAD_TIMEOUT, DOWNLOAD_WORKERS,
    MAX_THUMBNAILS, MIN_FACE_AREA_RATIO, SAME_PERSON_COSINE,
    SFACE_MIN_BYTES, SFACE_URL, THUMBNAIL_URL, YUNET_MIN_BYTES, YUNET_URL,
)

MODELS_DIR = Path(__file__).resolve().parent.parent / "models"
YUNET_PATH = MODELS_DIR / "face_detection_yunet_2023mar.onnx"
SFACE_PATH = MODELS_DIR / "face_recognition_sface_2021dec.onnx"


def _cv2():
    try:
        import cv2
        return cv2
    except ImportError:
        raise SystemExit("OpenCV manquant : pip install -r requirements-discovery.txt")


def _download_model(url: str, path: Path, min_bytes: int):
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    print(f"  Téléchargement du modèle {path.name} (une seule fois)...")
    resp = requests.get(url, timeout=180)
    resp.raise_for_status()
    if len(resp.content) < min_bytes:
        raise RuntimeError(
            f"Le fichier téléchargé pour {path.name} est trop petit ({len(resp.content)} octets) : "
            f"ce n'est pas le vrai modèle. Télécharge-le à la main depuis {url} et place-le dans {MODELS_DIR}."
        )
    path.write_bytes(resp.content)


def ensure_models():
    if not YUNET_PATH.exists() or YUNET_PATH.stat().st_size < YUNET_MIN_BYTES:
        _download_model(YUNET_URL, YUNET_PATH, YUNET_MIN_BYTES)
    if not SFACE_PATH.exists() or SFACE_PATH.stat().st_size < SFACE_MIN_BYTES:
        _download_model(SFACE_URL, SFACE_PATH, SFACE_MIN_BYTES)


class FaceAnalyzer:
    def __init__(self):
        cv2 = _cv2()
        ensure_models()
        self.cv2 = cv2
        self.detector = cv2.FaceDetectorYN.create(
            str(YUNET_PATH), "", (320, 320), DETECTOR_SCORE_THRESHOLD, 0.3, 5000)
        self.recognizer = cv2.FaceRecognizerSF.create(str(SFACE_PATH), "")

    def largest_face_embedding(self, img):
        """Retourne (embedding ou None, part de surface du plus grand visage)."""
        h, w = img.shape[:2]
        self.detector.setInputSize((w, h))
        _, faces = self.detector.detect(img)
        if faces is None or len(faces) == 0:
            return None, 0.0
        best = max(faces, key=lambda f: f[2] * f[3])
        area_ratio = float(best[2] * best[3]) / float(w * h)
        if area_ratio < MIN_FACE_AREA_RATIO:
            return None, area_ratio
        aligned = self.recognizer.alignCrop(img, best)
        return self.recognizer.feature(aligned), area_ratio

    def same_person(self, f1, f2) -> bool:
        score = self.recognizer.match(f1, f2, self.cv2.FaceRecognizerSF_FR_COSINE)
        return score >= SAME_PERSON_COSINE

    def analyze_images(self, images: list) -> dict:
        """images : liste d'images BGR (numpy). Retourne les chiffres de la chaîne."""
        n = len(images)
        embeddings = []
        for img in images:
            emb, _ = self.largest_face_embedding(img)
            if emb is not None:
                embeddings.append(emb)

        with_face = len(embeddings)

        # Plus grand groupe de miniatures montrant la même personne
        # (un pivot, puis tous les visages qui lui ressemblent).
        best_group = 0
        for i, e in enumerate(embeddings):
            group = 1 + sum(1 for j, o in enumerate(embeddings)
                            if j != i and self.same_person(e, o))
            best_group = max(best_group, group)
        same_count = best_group if best_group >= 2 else 0

        return {
            "images": n,
            "with_face": with_face,
            "face_ratio": round(with_face / n, 3) if n else 0.0,
            "same_face_count": same_count,
            "same_face_ratio": round(same_count / n, 3) if n else 0.0,
        }


def _decode(content: bytes):
    cv2 = _cv2()
    arr = np.frombuffer(content, dtype=np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if img is None:
        return None
    # hqdefault (480x360) contient des bandes noires haut/bas pour les vidéos 16:9 :
    # on garde la zone centrale 16:9, sinon la part de surface des visages serait faussée.
    h, w = img.shape[:2]
    if h > 0 and abs(w / h - 4 / 3) < 0.05:
        content_h = int(round(w * 9 / 16))
        top = (h - content_h) // 2
        img = img[top:top + content_h, :]
    return img


def fetch_thumbnail(video_id: str):
    url = THUMBNAIL_URL.format(video_id=video_id)
    for _ in range(2):
        try:
            resp = requests.get(url, timeout=DOWNLOAD_TIMEOUT)
            if resp.status_code == 200:
                return _decode(resp.content)
        except requests.RequestException:
            continue
    return None


def fetch_thumbnails(video_ids: list[str]) -> list:
    ids = list(dict.fromkeys(video_ids))[:MAX_THUMBNAILS]
    with ThreadPoolExecutor(max_workers=DOWNLOAD_WORKERS) as pool:
        images = list(pool.map(fetch_thumbnail, ids))
    return [img for img in images if img is not None]


def analyze_channel(video_ids: list[str], analyzer: FaceAnalyzer | None = None) -> dict:
    """Télécharge les miniatures des vidéos données et calcule les chiffres de la chaîne."""
    analyzer = analyzer or FaceAnalyzer()
    return analyzer.analyze_images(fetch_thumbnails(video_ids))


def _video_ids_of(channel: dict) -> list[str]:
    """Vidéos les plus vues d'une chaîne validée (sinon ses vidéos récentes)."""
    videos = (channel.get("strong_videos") or []) + (channel.get("proven_videos") or [])
    videos = sorted((v for v in videos if v.get("video_id")),
                    key=lambda v: v.get("view_count") or 0, reverse=True)
    ids = list(dict.fromkeys(v["video_id"] for v in videos))
    if not ids:
        ids = list(channel.get("recent_thumbnail_ids") or [])
    return ids[:MAX_THUMBNAILS]


def attach_face_scores(channels: list[dict]) -> None:
    """
    Ajoute face_ratio, same_face_ratio et face_checked_at à chaque chaîne validée (en place).
    Si OpenCV, les modèles ou le réseau ne sont pas disponibles, on saute cette étape
    sans bloquer la découverte : les chaînes sont enregistrées sans ces indices
    (rescan_faces.py pourra les calculer plus tard).
    """
    if not channels:
        return
    try:
        analyzer = FaceAnalyzer()
    except (SystemExit, Exception) as e:
        print(f"  (analyse des miniatures ignorée : {e})")
        return

    from datetime import datetime, timezone
    from config.face_settings import FACE_TAG_SAME_RATIO

    flagged = 0
    for i, c in enumerate(channels, 1):
        try:
            res = analyze_channel(_video_ids_of(c), analyzer)
        except Exception as e:
            print(f"  [{i}/{len(channels)}] {c.get('channel_title', '?')[:40]} : analyse impossible ({type(e).__name__})")
            continue
        if res["images"] == 0:
            continue
        c["face_ratio"] = res["face_ratio"]
        c["same_face_ratio"] = res["same_face_ratio"]
        c["face_checked_at"] = datetime.now(timezone.utc).isoformat()
        if res["same_face_ratio"] >= FACE_TAG_SAME_RATIO:
            flagged += 1
            print(f"  [{i}/{len(channels)}] {c.get('channel_title', '?')[:40]} -> Visage ? "
                  f"(même visage sur {res['same_face_ratio']:.0%} des miniatures)")
    print(f"  {flagged} chaîne(s) marquée(s) 'Visage ?' sur {len(channels)}.")


if __name__ == "__main__":
    args = sys.argv[1:]
    if not args:
        raise SystemExit(__doc__)
    cv2 = _cv2()
    an = FaceAnalyzer()
    if args[0] == "--image":
        imgs = [cv2.imread(p) for p in args[1:]]
        imgs = [i for i in imgs if i is not None]
        print(an.analyze_images(imgs))
    else:
        print(analyze_channel(args, an))