# CS6245 Parallelizing Compilers: Final project

## GPU shader optimization via automatic SPIRV subgroup transformations

### Broadcast

![broadcast](images/apply_broadcast_annotated.png)

### Reduce

![reduce](images/apply_reduce_annotated.png)

## Requirements

- [glslc](https://github.com/google/shaderc)
- [SPIRV-Tools](https://github.com/KhronosGroup/SPIRV-Tools)
- [SPIRV-Cross](https://github.com/KhronosGroup/SPIRV-Cross)
- [Python 3.10+](https://www.python.org/)

## Usage

```
$ python run.py filename [--validate | --no-validate] [--optimize | --no-optimize] [--show | --no-show] [--verbose | --no-verbose]
```

### Options

- `--validate`: Validate transformed SPIRV assembly (Default: false)
- `--optimize`: Optimize transformed SPIRV assembly (Default: true)
- `--show`:     Display cross-compiled GLSL code    (Default: true)
- `--verbose`:  Display additional debug logs       (Default: false)

### Examples

```
$ python run.py broadcast/before.comp --show
$ python run.py reduce/before.comp --show
```
