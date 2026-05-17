import sys
sys.path.insert(0, 'src')
from hamr.blender_bridge.e2e import execute_blender_build, E2EBuildConfig
from hamr.blender_bridge.runner import check_blender_available

print('Blender available:', check_blender_available())
if not check_blender_available():
    print('Blender not found, exiting.')
    sys.exit(1)

config = E2EBuildConfig(spec_name='anime_girl_default', gpu_profile='pi5', cleanup=False)
print('Config:', config)
result = execute_blender_build(config)
print('Result:', result)
if result.output_path:
    print('Output file exists:', result.output_path.exists())
