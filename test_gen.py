import sys
sys.path.insert(0, 'src')
from hamr.blender_bridge.e2e import generate_build_script, E2EBuildConfig
from hamr.blender_bridge.runner import check_blender_available

print('Blender available:', check_blender_available())
if not check_blender_available():
    print('Blender not found, exiting.')
    sys.exit(1)

config = E2EBuildConfig(spec_name='anime_girl_default', gpu_profile='pi5', cleanup=False)
script_path = generate_build_script(config)
print('Script path:', script_path)
print('Script content:')
print(script_path.read_text())
