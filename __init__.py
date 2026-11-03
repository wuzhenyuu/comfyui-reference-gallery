"""Local pose and costume references with their existing workflow interfaces."""
from . import pose
from .costume import CostumeGallery, RandomCostumeGallery

WEB_DIRECTORY = "./web"
NODE_CLASS_MAPPINGS = dict(pose.NODE_CLASS_MAPPINGS)
NODE_DISPLAY_NAME_MAPPINGS = dict(pose.NODE_DISPLAY_NAME_MAPPINGS)

# ComfyUI's legacy-mapping branch takes precedence over comfy_entrypoint.
# Initialize V3 metadata here before aggregating the two existing interfaces.
for node_class in (CostumeGallery, RandomCostumeGallery):
    schema = node_class.GET_SCHEMA()
    NODE_CLASS_MAPPINGS[schema.node_id] = node_class
    NODE_DISPLAY_NAME_MAPPINGS[schema.node_id] = schema.display_name
