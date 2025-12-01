#!/bin/bash

echo "Searching for __pycache__ folders..."

find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null


echo "Cleaned up all __pycache__ folders and Python cache files"