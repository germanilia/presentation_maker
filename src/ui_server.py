import base64
import json
import logging
import os
import subprocess
import sys
from pathlib import Path

from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from werkzeug.serving import WSGIRequestHandler
from werkzeug.utils import secure_filename

# Add logging configuration at the top after imports
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Disable Werkzeug request logs
WSGIRequestHandler.log = lambda self, type, message, *args: None

# Check if we're in development mode
DEV_MODE = os.getenv("FLASK_ENV") == "development"

# Set the static folder based on mode
static_folder = (
    str(Path(__file__).parent.parent / "ui" / "build") if not DEV_MODE else None
)

app = Flask(__name__, static_folder=static_folder)
# Enable CORS for all routes and origins
CORS(app, supports_credentials=True)

UPLOAD_FOLDER = "uploads"
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)


@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def serve(path):
    if DEV_MODE:
        # In development, only handle API requests
        return jsonify({"error": "Not found"}), 404
    else:
        # In production, serve the React app
        if path and static_folder and os.path.exists(os.path.join(static_folder, path)):
            return send_from_directory(static_folder, path)
        elif static_folder:
            return send_from_directory(static_folder, "index.html")
        else:
            return jsonify({"error": "Static folder not configured"}), 500


@app.route("/api/save-config", methods=["POST"])
def save_config():
    logger.info("Received save-config request")
    try:
        config = request.json
        if not config:
            logger.error("No configuration data received")
            return (
                jsonify(
                    {"status": "error", "message": "No configuration data received"}
                ),
                400,
            )

        # Create a copy of config for saving (to remove binary data)
        save_config = config.copy()

        # Handle logo if it's in base64 format
        if config.get("logo_base64"):
            try:
                # Extract the base64 data after the comma
                base64_data = config["logo_base64"].split(",")[1]
                logo_data = base64.b64decode(base64_data)
                logo_filename = f"logo_{secure_filename(config['topic'])}.png"
                logo_path = os.path.join(UPLOAD_FOLDER, logo_filename)

                with open(logo_path, "wb") as f:
                    f.write(logo_data)

                # Store the logo path instead of base64 data
                save_config["logo_path"] = logo_path
            except Exception as e:
                print(f"Error saving logo: {str(e)}")
                # Keep the base64 data if saving fails
                save_config["logo_path"] = ""
        else:
            save_config["logo_path"] = ""

        # Remove the base64 data before saving to JSON
        if "logo_base64" in save_config:
            del save_config["logo_base64"]

        # Save the configuration
        logger.info(f"Saving configuration for topic: {config.get('topic', 'unknown')}")
        with open("presentation-config.json", "w") as f:
            json.dump(save_config, f, indent=2)

        logger.info("Configuration saved successfully")
        return jsonify({"status": "success"})
    except Exception as e:
        logger.error(f"Error in save_config: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/generate", methods=["POST"])
def generate_presentation():
    logger.info("Received generate presentation request")
    try:
        # Get the config from the request
        data = request.get_json()
        logger.info(f"Received configuration data: {json.dumps(data, indent=2)}")

        if not data or "config" not in data:
            logger.error("No configuration data received")
            return (
                jsonify(
                    {"status": "error", "message": "No configuration data received"}
                ),
                400,
            )

        # Save the configuration
        config = data["config"]
        logger.info(
            f"Processing configuration for topic: {config.get('topic', 'unknown')}"
        )

        # Ensure the output directory exists
        os.makedirs("output", exist_ok=True)
        logger.info("Created output directory")

        # Save with proper permissions
        logger.info("Saving configuration to presentation-config.json")
        with open("presentation-config.json", "w") as f:
            json.dump(config, f, indent=2)

        # Handle logo if it's in base64 format
        if config.get("logo_base64"):
            try:
                logger.info("Processing logo data")
                logo_data = base64.b64decode(config["logo_base64"].split(",")[1])
                logo_filename = f"logo_{secure_filename(config['topic'])}.png"
                os.makedirs(UPLOAD_FOLDER, exist_ok=True)
                logo_path = os.path.join(UPLOAD_FOLDER, logo_filename)
                with open(logo_path, "wb") as f:
                    f.write(logo_data)
                logger.info(f"Logo saved to: {logo_path}")
            except Exception as e:
                logger.warning(f"Failed to save logo: {e}")

        # Get the path to main.py
        main_script = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), "main.py"
        )
        logger.info(f"Main script path: {main_script}")

        if not os.path.exists(main_script):
            logger.error(f"Main script not found at: {main_script}")
            return (
                jsonify(
                    {
                        "status": "error",
                        "message": f"Main script not found at {main_script}",
                    }
                ),
                500,
            )

        # Run the main.py script with real-time output handling
        logger.info(f"Running main script at: {main_script}")
        try:
            # Get the Python executable path
            python_executable = sys.executable
            process = subprocess.Popen(
                [python_executable, main_script],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                universal_newlines=True,
                env=os.environ.copy(),
            )

            output_lines = []
            while True:
                output_line = process.stdout.readline() if process.stdout else ""

                if output_line:
                    line = output_line.strip()
                    logger.info(f"Main script output: {line}")
                    output_lines.append(line)

                if not output_line and process.poll() is not None:
                    break

            return_code = process.poll()

            if return_code != 0:
                logger.error(f"Process failed with return code {return_code}")
                return (
                    jsonify(
                        {
                            "status": "error",
                            "message": "Process failed",
                            "details": "\n".join(output_lines),
                        }
                    ),
                    500,
                )

            # Check if presentation file was created
            expected_output = "output/presentation.pptx"
            if os.path.exists(expected_output):
                file_size = os.path.getsize(expected_output)
                logger.info(
                    f"Presentation file created successfully. Size: {file_size} bytes"
                )
                return jsonify(
                    {
                        "status": "success",
                        "message": "Presentation generated successfully",
                        "details": "\n".join(output_lines),
                    }
                )
            else:
                logger.error("Presentation file was not created")
                return (
                    jsonify(
                        {
                            "status": "error",
                            "message": "Presentation file was not created",
                            "details": "\n".join(output_lines),
                        }
                    ),
                    500,
                )

        except Exception as e:
            logger.error(f"Process error during generation: {str(e)}")
            return (
                jsonify({"status": "error", "message": f"Process error: {str(e)}"}),
                500,
            )

    except Exception as e:
        logger.error(f"Error in generate_presentation: {str(e)}")
        return jsonify({"status": "error", "message": f"Server error: {str(e)}"}), 500


@app.route("/api/load-config", methods=["GET"])
def load_config():
    logger.info("Received load-config request")
    try:
        if os.path.exists("sample-config.json"):
            logger.info("Loading configuration from sample-config.json")
            with open("sample-config.json", "r") as f:
                config = json.load(f)

            # If there's a logo path and the file exists, load it
            if config.get("logo_path") and os.path.exists(config["logo_path"]):
                with open(config["logo_path"], "rb") as f:
                    logo_data = f.read()
                    config["logo_base64"] = (
                        f"data:image/png;base64,{base64.b64encode(logo_data).decode()}"
                    )

            logger.info("Configuration loaded successfully")
            return jsonify(config)
        logger.info("No configuration file found")
        return jsonify({})
    except Exception as e:
        logger.error(f"Error in load_config: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/download/<filename>")
def download_file(filename):
    try:
        file_path = os.path.abspath(f"output/{filename}")
        if not os.path.exists(file_path):
            return (
                jsonify(
                    {"status": "error", "message": "No presentation file available"}
                ),
                404,
            )

        return send_from_directory(
            os.path.dirname(file_path),
            os.path.basename(filename),
            as_attachment=True,
        )
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


# Add new endpoint to check file existence
@app.route("/api/check-file/<folder>/<filename>")
def check_file(folder, filename):
    file_exists = os.path.exists(os.path.abspath(f"{folder}/{filename}"))
    return jsonify({"exists": file_exists})


if __name__ == "__main__":
    port = int(os.getenv("PORT", 9090))
    app.run(debug=True, host="0.0.0.0", port=port)
