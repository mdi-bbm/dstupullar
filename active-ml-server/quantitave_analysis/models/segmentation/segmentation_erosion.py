import os
import logging
import numpy as np
import cv2
from tqdm import tqdm
from autogluon.multimodal import MultiModalPredictor

from quantitave_analysis.utils.temporary_storage import TemporaryStorageManager, DataHandler
from quantitave_analysis.utils.image_processing import LabelPropertiesLoader
from quantitave_analysis.utils.file_converter import ConvertorPalette2Rgba
from quantitave_analysis.models.config import Config

ALL_MODELS_FOLDER = Config().ALL_MODELS_FOLDER


class SegmentationErosionProcessor:
    """
    Handles segmentation inference with morphological erosion post-processing.
    
    Recommended erosion parameters:
    - kernel_size=3, iterations=1 - minimal erosion
    - kernel_size=5, iterations=1 - moderate erosion
    - kernel_size=3, iterations=2 - stronger erosion
    """
    
    def __init__(self, model_handler_config):
        self.model_handler_config = model_handler_config
        self.temp_manager = TemporaryStorageManager()
    
    def apply_erosion(self, mask, kernel, iterations=1):
        """
        Applies morphological erosion to a mask with diagnostic logging.
        
        Args:
            mask: input mask (numpy array)
            kernel: morphological operation kernel
            iterations: number of erosion iterations
            
        Returns:
            eroded mask in the same format as input
        """
        try:
            # Convert to numpy array if needed
            if not isinstance(mask, np.ndarray):
                mask = np.array(mask)
            
            original_shape = mask.shape
            original_dtype = mask.dtype
            logging.info(f"Input mask - shape: {mask.shape}, dtype: {mask.dtype}")
            logging.info(f"Unique values in input: {np.unique(mask)}")
            
            # Remove batch dimension if present
            if len(mask.shape) == 3:
                if mask.shape[0] == 1:
                    mask_2d = mask[0]
                elif mask.shape[2] == 1:
                    mask_2d = mask[:, :, 0]
                else:
                    mask_2d = mask[:, :, 0]
            elif len(mask.shape) == 2:
                mask_2d = mask
            else:
                raise ValueError(f"Unexpected mask shape: {mask.shape}")
            
            # Check for non-zero pixels
            non_zero_count = np.count_nonzero(mask_2d)
            total_pixels = mask_2d.shape[0] * mask_2d.shape[1]
            logging.info(f"Non-zero pixels BEFORE erosion: {non_zero_count} / {total_pixels} ({100*non_zero_count/total_pixels:.2f}%)")
            
            if non_zero_count == 0:
                logging.warning("Input mask is completely empty! Skipping erosion.")
                return mask
            
            # Convert to uint8 for cv2.erode
            # Important: preserve class values, don't rescale!
            if mask_2d.dtype != np.uint8:
                max_val = mask_2d.max()
                if max_val <= 255:
                    mask_2d_uint8 = mask_2d.astype(np.uint8)
                else:
                    logging.warning(f"Mask has values > 255 (max: {max_val}). This may cause issues.")
                    mask_2d_uint8 = np.clip(mask_2d, 0, 255).astype(np.uint8)
            else:
                mask_2d_uint8 = mask_2d
            
            logging.info(f"Mask for erosion - shape: {mask_2d_uint8.shape}, dtype: {mask_2d_uint8.dtype}")
            logging.info(f"Unique values before erosion: {np.unique(mask_2d_uint8)}")
            
            # Apply erosion
            eroded_mask = cv2.erode(mask_2d_uint8, kernel, iterations=iterations)
            
            # Check result
            non_zero_after = np.count_nonzero(eroded_mask)
            logging.info(f"Non-zero pixels AFTER erosion: {non_zero_after} / {total_pixels} ({100*non_zero_after/total_pixels:.2f}%)")
            logging.info(f"Unique values after erosion: {np.unique(eroded_mask)}")
            
            if non_zero_after == 0:
                logging.error(f"⚠️ EROSION REMOVED ALL PIXELS! Original had {non_zero_count} pixels.")
                logging.error(f"Consider reducing kernel_size or iterations. Current: kernel_size={kernel.shape[0]}, iterations={iterations}")
            
            # Convert back to original dtype
            if original_dtype != np.uint8:
                eroded_mask = eroded_mask.astype(original_dtype)
            
            # Restore original dimensions
            if len(original_shape) == 3:
                if original_shape[0] == 1:
                    eroded_mask = np.expand_dims(eroded_mask, axis=0)
                elif original_shape[2] == 1:
                    eroded_mask = np.expand_dims(eroded_mask, axis=2)
            
            logging.info(f"Output mask - shape: {eroded_mask.shape}, dtype: {eroded_mask.dtype}")
            
            return eroded_mask
            
        except Exception as e:
            logging.error(f"Error in apply_erosion: {e}")
            logging.error(f"Original mask shape: {mask.shape}, dtype: {mask.dtype}")
            raise
    
    def remap_classes_for_convertor(self, mask):
        """
        Remaps class indices to sequential values starting from 0.
        ConvertorPalette2Rgba expects sequential class indices (0, 1, 2, ...).
        
        Args:
            mask: input mask with potentially non-sequential class values
            
        Returns:
            mask with remapped sequential class values
        """
        mask_for_save = mask.copy()
        unique_values = np.unique(mask_for_save)
        logging.info(f"Original unique values: {unique_values}")
        
        # If we have non-sequential classes (e.g., 0 and 2), remap them
        if len(unique_values) == 2 and 2 in unique_values:
            # Remap 2 -> 1 for compatibility with ConvertorPalette2Rgba
            mask_for_save[mask_for_save == 2] = 1
            logging.info(f"Remapped class 2 -> 1 for ConvertorPalette2Rgba")
            logging.info(f"New unique values: {np.unique(mask_for_save)}")
        
        return mask_for_save
    
    def save_and_verify_mask(self, eroded_mask, mask_file_path, label_properties):
        """
        Saves the mask and verifies it was saved correctly.
        
        Args:
            eroded_mask: the eroded mask to save
            mask_file_path: output file path
            label_properties: label properties for color mapping
            
        Returns:
            True if saved successfully, False otherwise
        """
        # Diagnostic before saving
        logging.info(f"Before save - eroded_mask shape: {eroded_mask.shape}, dtype: {eroded_mask.dtype}")
        logging.info(f"Before save - unique values: {np.unique(eroded_mask)}")
        logging.info(f"Before save - non-zero pixels: {np.count_nonzero(eroded_mask)}")
        
        # Remap classes if needed
        mask_for_save = self.remap_classes_for_convertor(eroded_mask)
        
        # Save using ConvertorPalette2Rgba
        ConvertorPalette2Rgba(
            label_properties=label_properties, 
            output=mask_file_path, 
            image_array=mask_for_save
        ).execute()
        
        # Verify saved file
        if os.path.exists(mask_file_path):
            saved_mask = cv2.imread(mask_file_path, cv2.IMREAD_UNCHANGED)
            if saved_mask is not None:
                logging.info(f"After save - saved file shape: {saved_mask.shape}, dtype: {saved_mask.dtype}")
                logging.info(f"After save - unique values: {np.unique(saved_mask)}")
                non_zero_saved = np.count_nonzero(saved_mask)
                logging.info(f"After save - non-zero pixels: {non_zero_saved}")
                
                if non_zero_saved == 0:
                    logging.error(f"⚠️ SAVED FILE IS EMPTY! Problem in ConvertorPalette2Rgba")
                    return False
                else:
                    logging.info(f"✓ File saved successfully with {non_zero_saved} non-zero pixels")
                    return True
            else:
                logging.error(f"Could not read saved file: {mask_file_path}")
                return False
        
        return False
    
    def run_predict_with_erosion(self, dataset_id: int, kernel_size=3, iterations=1):
        """
        Performs segmentation inference with morphological erosion.
        
        Args:
            dataset_id: dataset identifier
            kernel_size: size of erosion kernel (default: 3)
            iterations: number of erosion iterations (default: 1)
        """
        logging.info(f"Running segmentation inference with erosion (kernel_size={kernel_size}, iterations={iterations})...")

        folder_for_inference = os.path.normpath(self.model_handler_config.folder_for_inference)
        if not os.path.exists(folder_for_inference):
            raise FileNotFoundError(f"Data directory does not exist: {folder_for_inference}")

        models_base_folder = os.path.join(ALL_MODELS_FOLDER, str(dataset_id))
        model_directory = DataHandler.get_latest_model_path(
            base_folder=models_base_folder,
            model_name=self.model_handler_config.model_name
        )
        
        logging.info(f"Loading segmentation model from: {model_directory}")

        if not os.path.exists(model_directory):
            raise FileNotFoundError(f"Model directory does not exist: {model_directory}")

        # Load label properties
        label_properties_path = os.path.join(Config().UPLOAD_FOLDER, "label_properties.json")
        label_properties = LabelPropertiesLoader.load_label_properties(label_properties_path)
        logging.info(f"Loaded label properties for inference: {label_properties}")

        predictor_model = MultiModalPredictor.load(model_directory)

        results_folder_after_inference = os.path.normpath(self.model_handler_config.results_folder_after_inference)
        self.temp_manager.create_storage(results_folder_after_inference)

        # Create erosion kernel
        kernel = np.ones((kernel_size, kernel_size), np.uint8)
        
        successful = 0
        failed = 0
        empty_after_erosion = 0

        for img_file in tqdm(os.listdir(folder_for_inference)):
            img_path = os.path.normpath(os.path.join(folder_for_inference, img_file))
            if img_file.endswith('.png'):
                img_base_name = os.path.splitext(img_file)[0]
                try:
                    logging.info(f"\n{'='*60}")
                    logging.info(f"Processing: {img_file}")
                    
                    # Get prediction
                    prediction = predictor_model.predict({"image": [img_path]})
                    pred_array = prediction[0]
                    
                    # Apply erosion to mask
                    eroded_mask = self.apply_erosion(pred_array, kernel, iterations)
                    
                    # Check if anything remains after erosion
                    if np.count_nonzero(eroded_mask) == 0:
                        empty_after_erosion += 1
                        logging.warning(f"⚠️ Mask became empty after erosion for {img_file}")
                    
                    # Save result
                    mask_file_path = os.path.normpath(os.path.join(
                        results_folder_after_inference, 
                        f"{img_base_name}_mask.png"
                    ))
                    
                    if self.save_and_verify_mask(eroded_mask, mask_file_path, label_properties):
                        successful += 1
                        logging.info(f"✓ Successfully processed: {img_file}")
                    else:
                        failed += 1
                        logging.error(f"✗ Failed to save properly: {img_file}")

                except Exception as e:
                    failed += 1
                    logging.error(f"✗ Error processing image erosion {img_file}: {e}")
                    import traceback
                    logging.error(traceback.format_exc())
                    continue
            else:
                logging.info(f"Skipping unsupported file: {img_file}")

        logging.info(f"\n{'='*60}")
        logging.info(f"SUMMARY:")
        logging.info(f"Successful: {successful}")
        logging.info(f"Failed: {failed}")
        logging.info(f"Empty after erosion: {empty_after_erosion}")
        logging.info(f"Erosion parameters: kernel_size={kernel_size}, iterations={iterations}")
        
        if empty_after_erosion > 0:
            logging.warning(f"\n⚠️ {empty_after_erosion} masks became empty after erosion!")
            logging.warning(f"Consider using smaller parameters:")
            logging.warning(f"  - Current: kernel_size={kernel_size}, iterations={iterations}")
            logging.warning(f"  - Try: kernel_size=3, iterations=1 (minimal erosion)")
            logging.warning(f"  - Or: kernel_size=2, iterations=1 (very light erosion)")

        logging.info("Segmentation inference with erosion complete.")
    
    def apply_erosion_to_existing_masks(self, masks_folder, kernel_size=3, iterations=1):
        """
        Applies erosion to existing masks in a folder.
        
        Args:
            masks_folder: path to folder containing masks
            kernel_size: size of erosion kernel
            iterations: number of erosion iterations
        """
        kernel = np.ones((kernel_size, kernel_size), np.uint8)
        
        for mask_file in tqdm(os.listdir(masks_folder)):
            if mask_file.endswith('_mask.png'):
                mask_path = os.path.join(masks_folder, mask_file)
                
                try:
                    # Load mask
                    mask = cv2.imread(mask_path, cv2.IMREAD_GRAYSCALE)
                    
                    # Apply erosion
                    eroded_mask = cv2.erode(mask, kernel, iterations=iterations)
                    
                    # Save back (overwrite or create new version)
                    cv2.imwrite(mask_path, eroded_mask)
                    
                except Exception as e:
                    logging.error(f"Error processing mask {mask_file}: {e}")