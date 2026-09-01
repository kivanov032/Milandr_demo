from project.application.build import building_application
from requirements_check import install_requirements

try:
    from flet import *
    import cv2
    import torch
    # import gxipy ленивый импорт
    # import pyspacemouse ленивый импорт
    import numpy
    import serial
    import openpyxl
    import PIL
    import ultralytics

except ImportError:
    install_requirements()

app(target=building_application, assets_dir="assets")

# install_requirements()
