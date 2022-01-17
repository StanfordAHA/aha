declare -A conv_layer_args

conv_layer_args['conv1']='in_img=32 pad=3 ksize=7 stride=2 n_ic=3  n_oc=64 k_ic=3 k_oc=16'
conv_layer_args['conv2']='in_img=56 pad=1 ksize=3 stride=1 n_ic=32 n_oc=64 k_ic=8 k_oc=8'
conv_layer_args['conv3a']='in_img=56 pad=1 ksize=3 stride=2 n_ic=32 n_oc=128 k_ic=8 k_oc=8'
conv_layer_args['conv3b']='in_img=28 pad=1 ksize=3 stride=1 n_ic=32 n_oc=128 k_ic=8 k_oc=8'
conv_layer_args['conv4a']='in_img=28 pad=1 ksize=3 stride=2 n_ic=32 n_oc=256 k_ic=8 k_oc=8'
conv_layer_args['conv4b']='in_img=14 pad=1 ksize=3 stride=1 n_ic=32 n_oc=256 k_ic=8 k_oc=8'
conv_layer_args['conv5a']='in_img=14 pad=1 ksize=3 stride=2 n_ic=32 n_oc=512 k_ic=8 k_oc=8'
conv_layer_args['conv5b']='in_img=7 pad=1 ksize=3 stride=1 n_ic=32 n_oc=512 k_ic=8 k_oc=8'

log_folder="resnet_log_$(date +%Y%m%d_%H%M%S)"
mkdir ${log_folder}
for key in "${!conv_layer_args[@]}"; do
    {
        echo "$key ${conv_layer_args[$key]}";
        export HALIDE_GEN_ARGS="${conv_layer_args[$key]}";
        aha halide apps/resnet_output_stationary > "${log_folder}/${key}.halide.log";;
        aha map apps/resnet_output_stationary --width 32 --height 16 > "${log_folder}/${key}.map.log";
        cp ./Halide-to-Hardware/apps/hardware_benchmarks/apps/resnet_output_stationary/bin/resnet_output_stationary.bs "${log_folder}/${key}.bs";
    }
done
