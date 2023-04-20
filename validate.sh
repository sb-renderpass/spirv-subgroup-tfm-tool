spirv-as $1/after.comp.spvasm -o $1/after.comp.spv --preserve-numeric-ids
spirv-val $1/after.comp.spv
