## Directory Structure

- **ml_routines**
    - base.py — base class for ML routines
    - detection_routines.py — ML routines for detection tasks
    - segmentation_routines.py — ML routines for segmentation tasks

- active_server.py — checks for the presence of packages, creates a package, and runs jobs.py
- jobs.py — initiates the procedures for dataset creation, training, inference, and returning the result
- config.py — contains URL, user, and authentication