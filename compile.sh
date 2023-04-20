spirv-as broadcast/after.comp.spvasm -o broadcast/after.comp.spv
spirv-cross broadcast/after.comp.spv --output broadcast/after.comp --vulkan-semantics
cat broadcast/after.comp
