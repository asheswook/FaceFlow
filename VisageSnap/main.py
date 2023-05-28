import face_recognition
from dataclasses import dataclass
import os
import numpy as np
from sklearn.semi_supervised import LabelPropagation
from sklearn.exceptions import NotFittedError
import pickle
from typing import Generator, Union
from .classes import *
from .utils import *

class FaceProcessor:
    def __init__(self, globalState: GlobalState):
        self.__state = globalState

    def gen_faces(self) -> Generator[Face, None, None]:
        for face in self.__state.faces:
            yield face

    def convert_labelType(self, value: Union[str, int], to: str) -> any:
        """
        This function converts the label type. (numberLabel -> nameLabel, nameLabel -> numberLabel)

        Parameters
        ----------
        value (str or int) : target value.
        to (str) :
            - "To.NAME" : convert to name label.
            - "To.NUMBER" : convert to number label.

        Returns
        -------
        str or int : converted value. (if To.NAME, return str, if To.NUMBER, return int)
        """
        if to == "Name":
            for name, number in self.__state.label.items():
                if number == value:
                    return name
        elif to == "Number":
            return self.__state.label.get(value, -1)
        return None

    def set_label(self, person: Union[list, dict]) -> None:
        """
        This function sets the label dictionary.

        Parameters
        ----------
        person (list or dict) : label list or dictionary.

        Example
        -------
        person = ["name1", "name2", "name3", ...]

        OR

        person = {
            "name1": 0,
            "name2": 1,
            "name3": 2,
            ...
        }

        - name1, name2, name3, ... : name of the person
        - 0, 1, 2, ... : number label (MUST NOT BE -1)
        """

        if type(person) == dict:
            self.__state.label = person
        elif type(person) == list:
            for i in range(len(person)):
                self.__state.label[person[i]] = i

    def get_faceObject(self, target: str, value: str) -> Face:
        """
        This function returns the face object with the given label.

        Parameters
        ----------
        target:
            - "From.LABEL" : label of the face object. (name of the person)
            - "From.FILENAME" : filename of the face object.

        value (str) : value of the target.
        """
        assert isinstance(target, str), "target must be 'From.LABEL' or 'From.FILENAME'."
        assert isinstance(value, str), "value must be a string."

        for face in self.gen_faces():
            if target == "Label":
                if face.label == value:
                    return face
            elif target == "Filename":
                if value in face.filenames:
                    return face
        return None

class DirectoryManager:
    def __init__(self, directory: Directory):
        self.__directory = directory

    @property
    def dir(self) -> dict:
        """
        This function returns the directory.

        Returns
        -------
        dict (dict) : directory dictionary.

        Example
        -------
        dict = {
            "labeled": "labeled",
            "unlabeled": "unlabeled",
            "model": "model",
            "predict": "predict"
        }
        - labeled : directory of the labeled data
        - unlabeled : directory of the unlabeled data
        - model : directory of the model
        - predict : directory of the predict data

        Default
        -------
        labeled : "labeled"
        unlabeled : "unlabeled"
        model : "model"
        predict : "predict"
        """
        return self.__directory
    
    @dir.setter
    def dir(self, dicto: dict) -> None:
        def _set_dir(key: str, value: str):
            # Check if directory exists
            if os.path.isdir(value) == False:
                raise("The directory does not exist.")
            
            # Check if value is absoulte path or relative path. if relative, convert to absolute path.
            value = absp(value) if os.path.isabs(value) is False else value

            if key == "labeled":
                self.__directory.labeled = value
            elif key == "unlabeled":
                self.__directory.unlabeled = value
            elif key == "model":
                self.__directory.model = value
            elif key == "predict":
                self.__directory.predict = value

        for key, value in dicto.items():
            if key == "labeled":
                _set_dir(key, value)
            elif key == "unlabeled":
                _set_dir(key, value)
            elif key == "model":
                _set_dir(key, value)
            elif key == "predict":
                _set_dir(key, value)
            else:
                raise("The key is not valid.")
            

class ModelHandler:
    def __init__(self, globalState: GlobalState = None, directory: Directory = None):
        self.__state = globalState
        self.__directory = directory
        self.__state.model = self.load()

    def load(self) -> LabelPropagation:
        try:
            model_path = os.path.join(self.__directory.model, "face_model.pkl")

            with open(model_path, "rb") as f:
                self.__state.model, self.__state.faces = pickle.load(f)
                print("Model loaded.")

        except:
            print("Model not found. Creating new model...")
            self.__state.model = LabelPropagation()
            self.__state.faces = []  # 초기화

        return self.__state.model
        
    def save(self) -> None:
        model_path = os.path.join(self.__directory.model, "face_model.pkl")

        # Create directory if not exists
        os.mkdir(self.__directory.model) if not os.path.exists(self.__directory.model) else None

        with open(model_path, "wb") as f:
            pickle.dump((self.__state.model, self.__state.faces), f)  # Save as tuple


        if type(person) == dict:
            self.label = person
        elif type(person) == list:
            for i in range(len(person)):
                self.label[person[i]] = i
            
class ModelManager:
    def __init__(self):
        self.fp = FaceProcessor()

    def load(self) -> LabelPropagation:
        try:
            with open(self.fp.dir["model"], "rb") as f:
                self.model, self.fp.faces = pickle.load(f)
                print("Model loaded.")
                return self.model
        except: # 새 모델 만들기
            self.model = LabelPropagation()
            self.fp.faces = [] # 초기화
            return self.model
        
    def save(self) -> None:
        if not os.path.exists(absp("model")):
            os.mkdir(absp("model"))

        data = (self.model, self.fp.faces)
        with open(self.fp.dir["model"], "wb") as f:
            pickle.dump(data, f)

@singleton
class ImageLoader(FaceProcessor):
    def __init__(self):
        super().__init__()
    
    def __load_labeled(self) -> None: # 미리 주어지는 데이터는 한 사진에 한 사람만 있어야 한다.
        """
        This function loads the labeled data from the labeled directory.
        """
        for filename in gen(os.listdir(self.dir["labeled"])):
            if isimage(filename):
                label = (filename.split(".")[0]).split("-")[0] # 파일 형식은 이름-번호.jpg
                image = face_recognition.load_image_file(os.path.join(self.dir["labeled"], filename))
                encodings = face_recognition.face_encodings(image)
                encoding = encodings[0]
    
                # 만약 두개의 얼굴이 같은 사진에 있다면
                if len(encodings) > 1:
                    # 두개 이상의 얼굴... 시마이
                    continue

                # 만약 같은 얼굴이 있다면
                FACE_FOUND = False
                for i, face in enumerate(self.gen_faces): #얼굴 검색
                    if face.label == label: # 같은 얼굴이라면
                        for faceEncoding in face.encodings:
                            # 인코딩 같은게 있는지 확인
                            if np.array_equal(faceEncoding, encoding):
                                # 같은 게 있음
                                continue

                            # 인코딩이 다르다면 얼굴에 추가
                            self.faces[i].encodings.append(encoding)
                            self.faces[i].filenames.append(filename)
                            FACE_FOUND = True

                if not FACE_FOUND:
                    self.faces.append(Face(label, [encoding], [filename]))


    def __load_unlabeled(self) -> None:
        """
        This function loads the unlabeled data from the unlabeled directory.
        """
        for filename in gen(os.listdir(self.dir["unlabeled"])):
            if self._isImage(filename):
                image = face_recognition.load_image_file(os.path.join(self.dir["unlabeled"], filename))
                encodings = face_recognition.face_encodings(image)

                if len(encodings) == 0:
                    # 얼굴 감지 안됨
                    continue

                for encoding in encodings:
                    self.faces.append(Face("unknown", encoding, [filename]))


class Trainer(FaceProcessor):
    def __init__(self, modelManager: ModelManager = None):
        super().__init__()
        
        self.modelManager = modelManager
        self.il = ImageLoader()

    def __train(self, labeled: bool) -> None:
        assert isinstance(labeled, bool), "parameter must be boolean."

        if labeled:
            self.il.__load_labeled()
        else:
            self.il.__load_unlabeled()

        t_names = []
        t_encodings =[]

        for face in self.gen_faces():
            for encoding in face.encodings:
                numberLabel = self.convert_labelType(face.label, To.NUMBER)
                if labeled and numberLabel == -1: # 라벨링 데이터 학습인데 unknown이면 학습하지 않음
                    continue
                t_names.append(numberLabel)
                t_encodings.append(encoding)

        t_encodings = np.array(t_encodings)
        t_names = np.array(t_names)

        self.modelManager.model.fit(t_encodings, t_names)
        self._save_model()

    def train_labeled_data(self) -> None:
        self.__train(As.LABELED)

    def train_unlabeled_data(self) -> None:
        self.__train(As.UNLABELED)

class Predictor(FaceProcessor):
    def __init__(self, modelManager: ModelManager = None):
        super().__init__()

        self.modelManager = modelManager
        self.threshold = 0.48

    @staticmethod
    def __get_average(face: Face) -> np.array:
        """
        This function returns the average of the encodings.

        Parameters
        ----------
        face (Face) : target face.
        """
        assert isinstance(face, Face), "parameter must be Face class."
        return np.average(face.encodings, axis=0)

    @staticmethod
    def __get_distance(encoding1: np.ndarray, encoding2: np.ndarray) -> float:
        """
        This function returns the distance between two encodings.

        Parameters
        ----------
        encoding1 (np.array) : encoding1.
        encoding2 (np.array) : encoding2.
        """
        assert isinstance(encoding1, np.ndarray), "parameter must be numpy array."
        assert isinstance(encoding2, np.ndarray), "parameter must be numpy array."

        return np.linalg.norm(encoding1 - encoding2)

    def __isNotUnknown(self, encoding) -> bool:
        """
        This function checks whether the encoding is unknown.

        Parameters
        ----------
        encoding (np.array) : target encoding.
        """
        assert isinstance(encoding, np.ndarray), "parameter must be numpy array."

        min_distance = 1
        for face in self.gen_faces():
            print(face.label)
            average = self.__get_average(face) # 저장된 얼굴 평균 구하고
            distance = self.__get_distance(encoding, average) # 타겟과의 거리를 구한다
            if distance < min_distance:
                min_distance = distance

        if min_distance < self.threshold:
            return True # 모르는 사람이 아니다
        return False # 모르는 사람이다

    def __predict(self, image: np.ndarray) -> list:
        assert isinstance(image, np.ndarray), "parameter must be numpy array."

        target_encodings = face_recognition.face_encodings(image)
        if len(target_encodings) == 0:
            return None

        result = []
        for target_encoding in target_encodings:
            if self.__isNotUnknown(target_encoding): # 모르는 사람이 아니면
                result.append(self.modelManager.model.predict([target_encoding])[0])
            else:
                result.append(-1)

        return result



    def predict_all(self) -> dict:
        result = {}
        for filename in os.listdir(self.dir["predict"]):
            if isimage(filename) == False:
                return

            image = face_recognition.load_image_file(os.path.join(self.dir["predict"], filename))
            prediction = self.predict(image)

            if prediction == None:
                raise("There is no face in the image.")

            if len(prediction) == 1:
                result[filename] = self.convert_labelType(prediction[0], To.NAME)
            else:
                result[filename] = []
                for p in prediction:
                    result[filename].append(self.convert_labelType(p, To.NAME))
        return result
    
class Core(FaceProcessor):
    def __init__(self, modelManager: ModelManager = None):
        super().__init__()

        if modelManager is None:
            self.modelManager = ModelManager() # create New ModelManager Object
        else:
            self.modelManager = modelManager # or use the given ModelManager Object


        self.trainer = Trainer(modelManager)
        self.predictor = Predictor(modelManager)

    def train_labeled_data(self) -> None:
        self.trainer.train_labeled_data()

    def train_unlabeled_data(self) -> None:
        self.trainer.train_unlabeled_data()

    def predict(self, image: np.ndarray) -> list:
        return self.predictor.predict(image)
    
    def predict_all(self) -> dict:
        return self.predictor.predict_all()