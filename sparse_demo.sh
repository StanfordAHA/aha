#!/bin/bash

if [ $# -eq 0 ]; then
	echo "Error: please provide a command argument"
	exit 1
fi

command=$1

# Make SAM graphs 
case $command in 
	compile)
		echo "Setting up dependencies"
		cd sam/
		pip install -e .
		make submodules &> custard_log.txt

		# Build and Run Custard compiler
		echo "Build and run Custard compiler, log at sam/custard_log.txt"
		make taco/build &> custard_log.txt
		make sam &> custard_log.txt
		cd ..
	;;
	lower)
		cd sam/
		echo "Convert SAM graph to hardware-aware sparse dataflow graph"
		PYTHONPATH=/aha/garnet/ python sam/onyx/parse_dot.py --sam_graph /aha/sam/compiler/sam-outputs/onyx-dot/mat_elemadd.gv --output_png hw_aware_mat_elemadd.png --output_graph hw_aware_mat_elemadd.gv  
		cd ..
	;;
	gen)
		echo "Map to sparse CGRA and generate bitstream"
		EXHAUSTIVE_PIPE=1 PYTHONPATH=/aha/garnet/ python /aha/garnet/tests/test_memory_core/build_tb.py --ic_fork --sam_graph /aha/sam/compiler/sam-outputs/onyx-dot/mat_elemadd.gv --seed 0 --dump_bitstream --add_pond --combined --pipeline_scanner --base_dir /aha/garnet/SPARSE_TESTS/ --just_glb --dump_glb --fiber_access --width 12 --height 4
	;;
	*)
		echo "Invalid command: $command"
		exit 1
	;;
esac
