import numpy as np
from PIL import Image
from typing import List
import numpy.typing as npt
import pandas as pd
from quantitave_analysis.augmentations.segmentation_augmentations import SampleProcessor
from quantitave_analysis.utils.file_converter import ConvertorWebp2Png
def save_image_to_palette(
        image: npt.NDArray,
        palette: List[List[int]],
        save_path: str
) -> None:
    """Save an image as a palette-based PNG

    Args:
        image: An indexed numpy array where each value is an index into the palette
        palette: A list of RGB colors, where each color is a list of [R, G, B] values
        save_path: Path where to save the image
    """
    # Convert the numpy array to a PIL image in mode 'P' (palette)
    image = Image.fromarray(image.astype(np.uint8)).convert("P")

    # Convert palette to flat list as required by putpalette
    flat_palette = [value for color in palette for value in color]

    # Apply palette to the image
    image.putpalette(flat_palette)

    # Save the image
    image.save(save_path)

def hex_to_rgb(hex_color):
    """Convert hex color string to RGB tuple"""
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i + 2], 16) for i in (0, 2, 4))

# TRAIN

# label_properties = {'Standart_label': '#FF0000', 'Second_label': '#14FF00'}
#
# # Получаем значения и преобразуем их в список
# colors_list = list(label_properties.values())
#
# palette = [[0,0,0]]
# for i in range(len(colors_list)):
#     palette.append(hex_to_rgb(colors_list[i]))
# print(palette)
#
# path = "C:/Users/cheka/Downloads/446_cx43_Z000_cx43_dd6d1651_confocal_brain_cortex_healthy_rat_mask.png"
#
# data_table = pd.DataFrame(columns=["index", "image", "label"])
# base_name = path.split('.')[0]
# SampleProcessor().process(path, path, base_name, data_table)

ConvertorWebp2Png(input = "D:\\PyCharm Community Edition 2023.3.4\\projects\\work\\digitalassistantmonorepo\\quantitave_analysis\\447_cx43_Z00_cx43_0be8973d_confocal_brain_cortex_awake_bat_mask.webp",
                  output = "D:\\PyCharm Community Edition 2023.3.4\\projects\\work\\digitalassistantmonorepo\\quantitave_analysis\\447_cx43_Z00_cx43_0be8973d_confocal_brain_cortex_awake_bat_mask.png").execute()

# img = Image.open(path)
# img_arr = np.array(img)
#
# # Создаем палитровое изображение
# height, width = img_arr.shape[:2]
# palette_image = np.zeros((height, width), dtype=np.uint8)
#
# # Преобразуем палитру в numpy массив
# palette_np = np.array(palette)
#
# # Берем только RGB каналы изображения
# rgb_pixels = img_arr[:, :, :3].reshape(-1, 3)
#
# # Вычисляем матрицу расстояний от каждого пикселя до каждого цвета палитры
# # Преобразуем форму данных для широковещательных операций
# pixels_expanded = rgb_pixels.reshape(-1, 1, 3)
# palette_expanded = palette_np.reshape(1, -1, 3)
#
# # Вычисляем квадрат евклидова расстояния
# distances = np.sum((pixels_expanded - palette_expanded) ** 2, axis=2)
#
# # Находим индекс ближайшего цвета для каждого пикселя
# nearest_indices = np.argmin(distances, axis=1)
#
# # Преобразуем обратно в форму изображения
# palette_image = nearest_indices.reshape(height, width)
#
# save_image_to_palette(
#     palette_image,
#     palette,
#     "C:/Users/cheka/Downloads/446_cx43_Z000_cx43_dd6d1651_confocal_brain_cortex_healthy_rat_mask_palette.png"
# )


# # INFERENCE
#
# # Загрузка изображения с индексами
# palette_image = Image.open("C:/Users/cheka/Downloads/446_cx43_Z000_cx43_dd6d1651_confocal_brain_cortex_healthy_rat_mask_palette.png")
# palette_arr = np.array(palette_image)
# # print(palette_arr)
#
# # Создаем новое изображение с RGBA
# height, width = palette_arr.shape
# rgba_image = np.zeros((height, width, 4), dtype=np.uint8)
#
# # Создаем маски для каждого индекса в палитре
# for index, color in enumerate(palette):
#     mask = (palette_arr == index)
#     rgba_image[mask, :3] = color
#
#     # Устанавливаем альфа-канал (0 для индекса 0, 255 для остальных)
#     rgba_image[mask, 3] = 0 if index == 0 else 255
#
# # Создаем изображение из массива
# rgba_image_pil = Image.fromarray(rgba_image, mode='RGBA')
#
# # Сохраняем новое изображение
# rgba_image_pil.save("C:/Users/cheka/Downloads/converted_image.png")
#
# print(np.array_equal(rgba_image, img_arr))
# print(np.allclose(rgba_image, img_arr, atol=1e-8))