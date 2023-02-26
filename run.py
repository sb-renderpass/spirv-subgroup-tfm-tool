import argparse
import subprocess

BEFORE = 'before'
AFTER  = 'after'

def run(path, verbose, validate, optimize, show):
    subprocess.run([
        'glslc',
        f'{path}/{BEFORE}.comp',
        '--target-env=vulkan1.3',
        '--target-spv=spv1.6',
        '-o', f'{path}/{BEFORE}.spv'],
        check=True)

    subprocess.run([
        'spirv-dis',
        f'{path}/{BEFORE}.spv',
        '-o', f'{path}/{BEFORE}.spvasm'],
        check=True)

    subprocess.run([
        'python',
        'main.py',
        '-i', f'{path}/{BEFORE}.spvasm',
        '-o', f'{path}/{AFTER}.spvasm',
        '--verbose' if verbose else '--no-verbose'],
        check=True)

    subprocess.run([
        'spirv-as',
        f'{path}/{AFTER}.spvasm',
        '-o', f'{path}/{AFTER}.spv'],
        check=True)

    if validate:
        subprocess.run([
            'spirv-val',
            f'{path}/{AFTER}.spv'],
            check=True)

    subprocess.run([
        'spirv-as',
        f'{path}/{AFTER}.spvasm',
        '-o', f'{path}/{AFTER}.spv'],
        check=True)

    if optimize:
        subprocess.run([
            'spirv-opt',
            f'{path}/{AFTER}.spv',
            '-o', f'{path}/{AFTER}.spv',
            '-O', '--skip-validation'],
        check=True)

    subprocess.run([
        'spirv-cross',
        f'{path}/{AFTER}.spv',
        '--output', f'{path}/{AFTER}.comp',
        '--vulkan-semantics'],
        check=True)

    if show:
        subprocess.run([
            'cat',
            f'{path}/{AFTER}.comp'],
        check=True)

def main():
    parser = argparse.ArgumentParser('SPIRV subgroup transform')
    parser.add_argument('path', type=str)
    parser.add_argument('--verbose',  action=argparse.BooleanOptionalAction, default=False)
    parser.add_argument('--validate', action=argparse.BooleanOptionalAction, default=False)
    parser.add_argument('--optimize', action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument('--show',     action=argparse.BooleanOptionalAction, default=False)
    args = parser.parse_args()

    try:
        run(args.path, args.verbose, args.validate, args.optimize, args.show)
    except subprocess.CalledProcessError as exc:
        print(f'ERROR: {exc}')

if __name__ == '__main__':
    main()

