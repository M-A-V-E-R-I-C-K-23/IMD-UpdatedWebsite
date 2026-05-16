#!/bin/bash
sshpass -p 'mwomumbai@4321' rsync -avz --exclude '.git' --exclude 'node_modules' --exclude '.venv' --exclude '__pycache__' ./ mwomumbai@121.240.10.8:~/mwo_website/
sshpass -p 'mwomumbai@4321' ssh -t mwomumbai@121.240.10.8 "cd ~/mwo_website && echo 'mwomumbai@4321' | sudo -S docker compose up -d --build"
