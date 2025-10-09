# # Create folder ./id_garden if not exists
# if [ ! -d "./id_garden" ]; then
#   mkdir ./id_garden
# fi
# # Remove all files in id_garden
# rm -rf ./id_garden/*
# Down and up docker-compose
sudo docker compose down calcubot -v
sudo docker compose up --build --force-recreate -d