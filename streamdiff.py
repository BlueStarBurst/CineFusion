# -*- coding: utf-8 -*-
"""StreamDiffusionImg2Img_colab.ipynb

Automatically generated by Colab.

Original file is located at
    https://colab.research.google.com/drive/114zR1eeJfXH4aotosubtiWlBSz9lWgja
"""

# Commented out IPython magic to ensure Python compatibility.
# %load_ext autoreload
# %autoreload 2

# Commented out IPython magic to ensure Python compatibility.
# %cd /content

import torch

from diffusers import AutoPipelineForInpainting, AutoencoderTiny, StableDiffusionPipeline, StableDiffusionInpaintPipeline
from diffusers.utils import load_image, make_image_grid

print(torch.cuda.is_available())


init_image = load_image("https://huggingface.co/datasets/huggingface/documentation-images/resolve/main/diffusers/inpaint.png")
mask_image = load_image("https://huggingface.co/datasets/huggingface/documentation-images/resolve/main/diffusers/inpaint_mask.png")

print(mask_image)

import cv2
from PIL import Image
import numpy as np


import os
import sys
# sys.path.append("/content/StreamDiffusion")


sys.path.append("./StreamDiffusion")
sys.path.append("./StreamDiffusion/src")

# sys.path.append("./RealStream")
# sys.path.append("./RealStream/src")

from streamdiffusion.pipeline import StreamDiffusion
from streamdiffusion.image_utils import postprocess_image, process_image



from utils.wrapper import StreamDiffusionWrapper

# Wrap the pipeline in StreamDiffusion
# Requires more long steps (len(t_index_list)) in text2image
# You should use cfg_type="none" when text2image
# stream = StreamDiffusionWrapper(
#         model_id_or_path="stabilityai/sd-turbo",
#         lora_dict=None,
#         t_index_list=[5,22,32,45],
#         frame_buffer_size=1,
#         width=512,
#         height=512,
#         warmup=1,
#         acceleration="tensorrt",
#         mode="img2img",
#         use_denoising_batch=True,
#         cfg_type="self",
#         seed=2,
#     )

stream = StreamDiffusionWrapper(
        model_id_or_path="stabilityai/sd-turbo",
        lora_dict=None,
        t_index_list=[22, 32, 45],
        frame_buffer_size=1,
        width=512,
        height=512,
        warmup=2,
        acceleration="xformers",
        mode="img2img",
        use_denoising_batch=True,
        cfg_type="self",
        seed=2,
    )

prompt = "realistic, batman, mask"
# prompt = "realistic, mount rushmore"
# prompt = "realistic, volcano, magma, lava, fire, red"
negative_prompt = "cartoon, smoke, grey"
# Prepare the stream
stream.prepare(
    prompt=prompt,
    negative_prompt=negative_prompt,
    num_inference_steps=50,
    guidance_scale=1.2,
    delta=0.5,
)

# Prepare image
# init_image = load_image("/content/StreamDiffusion/assets/img2img_example.png").resize((512, 512))

# print(image_tensor.size())

def setprompt(prompt, negative_prompt):
    stream.prepare(
        prompt=prompt,
        negative_prompt=negative_prompt,
        num_inference_steps=50,
        guidance_scale=1.2,
        delta=0.5,
    )

def streamdiffusion(image, mask=None):
    
    image = Image.fromarray(image)
    
    maskArr = np.array(mask)
    
    # print(maskArr.shape, maskArr[256][256])
    
    # print(maskArr.shape)
    # make 3 channels (512, 512) -> (512, 512, 3) with numpy
    # print(maskArr.shape)
    maskArr = np.stack((maskArr,)*3, axis=-1)
    # print(maskArr.shape)
    # print(maskArr.shape)
    
    blurred_mask_image = cv2.blur(maskArr, (35,35))
    
    # print(blurred_mask_image.shape)
    
    # make 3 channels (512, 512) -> (512, 512, 3)
    # blurred_mask_image = cv2.cvtColor(blurred_mask_image, cv2.COLOR_GRAY2RGB)
    
    # blurred_mask_image = Image.fromarray(blurred_mask_image)
    blurred_mask_image = np.array(blurred_mask_image)/255
    
    # print(blurred_mask_image.shape, blurred_mask_image[256][256][0])
    
    process_start = cv2.getTickCount()
    image_tensor = stream.preprocess_image(image)
    process_end = cv2.getTickCount()
    process_fps = cv2.getTickFrequency() / (process_end - process_start)
    # print("PROCESS FPS:", process_fps)
    
    stream_start = cv2.getTickCount()
    output_image = stream(image_tensor, mask=blurred_mask_image)
    # output_image = stream(image_tensor)
    stream_end = cv2.getTickCount()
    stream_fps = cv2.getTickFrequency() / (stream_end - stream_start)
    # print("STREAM FPS:", stream_fps)
    
    mask = (np.array(blurred_mask_image)).astype(np.float16)
    output_arr = np.array(output_image)

    # print(mask.shape)
    # print(mask[256][256][0])
    # print(output_arr.shape)

    fixed = output_arr * mask + image * (1-mask)
    fixed = fixed.astype(np.uint8)

    # output_image
    return Image.fromarray(fixed)

# if main
if __name__ == "__main__":
    while True:
        streamdiffusion(np.array(init_image), mask_image)