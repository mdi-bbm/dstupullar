from quantitave_analysis.models.segmentation.segmentation_model import SegmentationModelHandler
from quantitave_analysis.models.config import Config

ALL_MODELS_FOLDER = Config().ALL_MODELS_FOLDER
PROCESSED_FOLDER = Config().PROCESSED_FOLDER
UPLOAD_FOLDER = Config().UPLOAD_FOLDER
RETURN_FOLDER = Config().RETURN_FOLDER

# Creating an instance of the SegmentationModelHandler class
segmentation_handler = SegmentationModelHandler()

# Calling the run_train method to train the model
segmentation_handler.run_train(PROCESSED_FOLDER, ALL_MODELS_FOLDER)

# Calling the run_predict method to make a prediction
segmentation_handler.run_predict(UPLOAD_FOLDER, RETURN_FOLDER)