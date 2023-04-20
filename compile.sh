spirv-as $1/after.comp.spvasm -o $1/after.comp.spv --preserve-numeric-ids
spirv-cross $1/after.comp.spv --output $1/after.comp --vulkan-semantics
cat $1/after.comp
