#!/bin/bash

# Se nenhum argumento for fornecido, use o projeto padrão
if [ $# -eq 0 ]; then
  projeto="lorawan-base"
  commit="First commit"
else
  projeto=$1
  commit=$2
fi

# gh repo create

# Restante do script
git init
git add .
git status
git commit -m "$commit"
git branch -M main
git remote add origin "https://github.com/geraldosarmento/$projeto.git"
git push --force -u origin main

