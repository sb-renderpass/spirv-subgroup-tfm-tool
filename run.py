import argparse
import pathlib
import subprocess

BEFORE = 'before'
AFTER  = 'after'

def run(filename, verbose, validate, optimize, show):
    path = filename.parent

    subprocess.run([
        'glslc',
        f'{filename}',
        '--target-env=vulkan1.3',
        '--target-spv=spv1.6',
        '-o', f'{path}/{BEFORE}.comp.spv'],
        check=True)

    subprocess.run([
        'spirv-dis',
        f'{path}/{BEFORE}.comp.spv',
        '-o', f'{path}/{BEFORE}.comp.spvasm'],
        check=True)

    subprocess.run([
        'python',
        'tool.py',
        '-i', f'{path}/{BEFORE}.comp.spvasm',
        '-o', f'{path}/{AFTER}.comp.spvasm',
        '--verbose' if verbose else '--no-verbose'],
        check=True)

    subprocess.run([
        'spirv-as',
        f'{path}/{AFTER}.comp.spvasm',
        '-o', f'{path}/{AFTER}.comp.spv',
        '--preserve-numeric-ids'],
        check=True)

    if validate:
        subprocess.run([
            'spirv-val',
            f'{path}/{AFTER}.comp.spv'],
            check=True)

    if optimize:
        subprocess.run([
            'spirv-opt',
            f'{path}/{AFTER}.comp.spv',
            '-o', f'{path}/{AFTER}.comp.spv',
            '-O', '--skip-validation'],
        check=True)

    subprocess.run([
        'spirv-cross',
        f'{path}/{AFTER}.comp.spv',
        '--output', f'{path}/{AFTER}.comp',
        '--vulkan-semantics'],
        check=True)

    if show:
        subprocess.run([
            'cat',
            f'{path}/{AFTER}.comp'],
        check=True)

def main():
    parser = argparse.ArgumentParser('SPIRV subgroup transformation')
    parser.add_argument('filename',   type=pathlib.Path)
    parser.add_argument('--validate', action=argparse.BooleanOptionalAction, default=False, help='Validate transformed SPIRV assembly')
    parser.add_argument('--optimize', action=argparse.BooleanOptionalAction, default=True,  help='Optimize transformed SPIRV assembly')
    parser.add_argument('--show',     action=argparse.BooleanOptionalAction, default=False, help='Display cross-compiled GLSL code')
    parser.add_argument('--verbose',  action=argparse.BooleanOptionalAction, default=False, help='Display additional debug logs')
    args = parser.parse_args()

    try:
        run(args.filename, args.verbose, args.validate, args.optimize, args.show)
    except subprocess.CalledProcessError as exc:
        print(f'ERROR: {exc}')

if __name__ == '__main__':
    main()

