BUILD_DIR=build
include $(N64_INST)/include/n64.mk
include $(N64_INST)/include/t3d.mk

N64_CFLAGS += -std=gnu2x
src = src/main.c
assets_gltf = $(wildcard assets/*.glb)
assets_conv = $(addprefix filesystem/,$(notdir $(assets_gltf:%.glb=%.t3dm)))

all: PENNYWISE64_PASS5.z64

filesystem/%.t3dm: assets/%.glb tools/sanitize_materials.py
	@mkdir -p $(dir $@)
	@echo "    [SANITIZE] $<"
	python3 tools/sanitize_materials.py "$<"
	@echo "    [T3D-MODEL] $@"
	$(T3D_GLTF_TO_3D) "$<" $@
	$(N64_BINDIR)/mkasset -c 2 -w 256 -o filesystem $@

$(BUILD_DIR)/PENNYWISE64_PASS5.dfs: $(assets_conv)
$(BUILD_DIR)/PENNYWISE64_PASS5.elf: $(src:%.c=$(BUILD_DIR)/%.o)
PENNYWISE64_PASS5.z64: N64_ROM_TITLE="PENNYWISE 64 P5"
PENNYWISE64_PASS5.z64: N64_ROM_CONTROLLER1=n64
PENNYWISE64_PASS5.z64: $(BUILD_DIR)/PENNYWISE64_PASS5.dfs

clean:
	rm -rf $(BUILD_DIR) filesystem *.z64

-include $(wildcard $(BUILD_DIR)/*.d)
.PHONY: all clean
