if [ "$1" = "mine" ]
then
cd APEX
pip install -r requirements.txt
python dse_graph_analysis.py -f ../Halide-to-Hardware/apps/hardware_benchmarks/apps/gaussian/bin/gaussian_compute.json 20 -f ../Halide-to-Hardware/apps/hardware_benchmarks/apps/harris/bin/harris_compute.json 20 --subgraph-mining-only
cd ..
fi

if [ "$1" = "specialize" ]
then
cd APEX
python dse_graph_analysis.py -f ../Halide-to-Hardware/apps/hardware_benchmarks/apps/gaussian/bin/gaussian_compute.json 1 -f ../Halide-to-Hardware/apps/hardware_benchmarks/apps/harris/bin/harris_compute.json 0 6 -c
cd ..
fi
