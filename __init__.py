"""Local pose, costume and hairstyle references with existing workflow interfaces."""
from . import pose
from . import hairstyle
from .costume import CostumeGallery, RandomCostumeGallery

WEB_DIRECTORY = "./web"
NODE_CLASS_MAPPINGS = dict(pose.NODE_CLASS_MAPPINGS)
NODE_DISPLAY_NAME_MAPPINGS = dict(pose.NODE_DISPLAY_NAME_MAPPINGS)
NODE_CLASS_MAPPINGS.update(hairstyle.NODE_CLASS_MAPPINGS)
NODE_DISPLAY_NAME_MAPPINGS.update(hairstyle.NODE_DISPLAY_NAME_MAPPINGS)

# ComfyUI's legacy-mapping branch takes precedence over comfy_entrypoint.
# Initialize V3 metadata here before aggregating the existing interfaces.
for node_class in (CostumeGallery, RandomCostumeGallery):
    schema = node_class.GET_SCHEMA()
    NODE_CLASS_MAPPINGS[schema.node_id] = node_class
    NODE_DISPLAY_NAME_MAPPINGS[schema.node_id] = schema.display_name
