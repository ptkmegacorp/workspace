# manager-worker-flow-test

A test project for the manager-worker agent architecture.

## What this does

This project demonstrates a bash script that:
- Finds all image files (jpg, png, gif, webp, bmp) in a given directory
- Renames them with a standardized format: `{prefix}_{timestamp}_{originalname}.{ext}`
- Uses pipes and filters to process files cleanly

## Usage

```bash
./rename-images.sh <directory> [prefix]
```

### Examples

Rename all images in current directory with default prefix:
```bash
./rename-images.sh ./photos
```

Rename with custom prefix:
```bash
./rename-images.sh ./photos vacation
```

## Testing the manager-worker architecture

This script is designed to be run by a **worker agent** that:
1. Receives only the necessary context (directory path, prefix)
2. Executes the task independently
3. Reports results back to the manager

The manager coordinates multiple such workers for parallel tasks.
