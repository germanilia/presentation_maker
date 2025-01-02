import json
import logging
import os
from pathlib import Path

from models.presentation_config import PresentationConfig


class StorageHandler:
    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def load_presentation_config(self, config_path) -> PresentationConfig:
        self.logger.info(f"Loading presentation config from: {config_path}")
        try:
            try:
                with open(config_path, "r") as f:
                    config_data = f.read()
                self.logger.debug("Successfully read config file")
            except Exception as e:
                self.logger.error(f"Failed to load config file: {str(e)}")
                raise Exception(f"Failed to load config file from local path: {str(e)}")

            config_dict = json.loads(config_data)
            config = PresentationConfig.model_validate(config_dict)
            self.logger.info("Successfully loaded and validated presentation config")
            return config
        except json.JSONDecodeError as e:
            self.logger.error(f"Invalid JSON in config file: {str(e)}")
            raise Exception(f"Invalid JSON in config file: {str(e)}")
        except Exception as e:
            self.logger.error(f"Error loading presentation config: {str(e)}")
            raise Exception(f"Error loading presentation config: {str(e)}")

    def save_presentation(self, prs, output_path):
        self.logger.info(f"Saving presentation to: {output_path}")
        output_dir = os.path.dirname(output_path)
        if output_dir:
            full_dir_path = (
                f'{output_dir}/{output_path.replace(".","").replace("/","")}'
            )
            self.logger.debug(f"Creating output directory: {full_dir_path}")
            os.makedirs(full_dir_path, exist_ok=True)

        save_path = f"{output_path}/presentation.pptx"
        self.logger.info(f"Saving presentation file to: {save_path}")
        prs.save(save_path)
        self.logger.info("Presentation saved successfully")

    def clear_output_folder(self, output_path):
        """Deletes all contents of the specified output folder while preserving the folder itself."""
        self.logger.info(f"Clearing output folder: {output_path}")
        try:
            output_dir = Path(output_path)
            if output_dir.exists():
                # Delete contents but keep the directory
                for item in output_dir.iterdir():
                    if item.is_file():
                        self.logger.debug(f"Deleting file: {item}")
                        item.unlink()
                    elif item.is_dir():
                        self.logger.debug(f"Deleting directory: {item}")
                        import shutil

                        shutil.rmtree(item)
                self.logger.info("Output folder cleared successfully")
            else:
                self.logger.warning(f"Output directory does not exist: {output_path}")
        except Exception as e:
            self.logger.error(f"Failed to clear output folder: {str(e)}")
            raise Exception(f"Failed to clear local output folder contents: {str(e)}")
