from mtcnn import MTCNN
from keras_facenet import FaceNet

print("Loading core models (FaceNet, MTCNN)...")
facenet = FaceNet().model
detector = MTCNN()

svm_model = None
label_encoder = None
yolo_medicine_model = None
yolo_general_model = None
