"""
Réglages de la détection de visages sur les miniatures (partie B).

Les seuils de TAG (FACE_TAG_*) sont provisoires : on les ajuste avec
`python -m discovery.calibrate_faces` à partir de tes chaînes supprimées
"Visage" et de tes chaînes gardées.
"""

# Nombre de miniatures analysées par chaîne.
MAX_THUMBNAILS = 6

# Un visage ne compte que s'il occupe au moins cette part de la miniature
# (0.02 = 2 % de la surface). Ça ignore les petits visages de fond.
MIN_FACE_AREA_RATIO = 0.02

# Confiance minimale du détecteur YuNet (0 à 1).
DETECTOR_SCORE_THRESHOLD = 0.8

# Seuil de similarité cosinus de SFace : au-dessus = même personne.
# 0.363 est la valeur recommandée par OpenCV pour SFace.
SAME_PERSON_COSINE = 0.363

# Provisoires, à confirmer par la calibration :
FACE_TAG_SAME_RATIO = 0.50   # part des miniatures montrant la même personne -> tag "Visage ?"

# Téléchargement des miniatures.
THUMBNAIL_URL = "https://i.ytimg.com/vi/{video_id}/hqdefault.jpg"
DOWNLOAD_TIMEOUT = 10
DOWNLOAD_WORKERS = 6

# Modèles OpenCV (téléchargés une fois dans le dossier models/ du projet).
YUNET_URL = ("https://media.githubusercontent.com/media/opencv/opencv_zoo/main/"
             "models/face_detection_yunet/face_detection_yunet_2023mar.onnx")
SFACE_URL = ("https://media.githubusercontent.com/media/opencv/opencv_zoo/main/"
             "models/face_recognition_sface/face_recognition_sface_2021dec.onnx")
YUNET_MIN_BYTES = 100_000
SFACE_MIN_BYTES = 30_000_000