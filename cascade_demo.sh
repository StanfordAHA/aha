cd /aha/

pip install Pillow

POST_PNR_ITR=$1 PYTHONPATH=/aha/garnet/ python /aha/garnet/tests/test_memory_core/build_tb.py --ic_fork --sam_graph /aha/sam/compiler/sam-outputs/onyx-dot/mat_elemadd.gv --seed 0 --dump_bitstream --add_pond --combined --pipeline_scanner --base_dir /aha/garnet/SPARSE_TESTS/ --just_glb --dump_glb --fiber_access --width 12 --height 4

python archipelago/archipelago/sta.py -a garnet/SIM_DIR/ -v --sparse

