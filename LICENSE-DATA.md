# Data licence

The code in this repository (`src/`, `scripts/`, `tests/`, `notebooks/`, `report/*.py`) is released under the MIT
licence in `LICENSE`. Everything else it produces or ships as data is released under the
**Creative Commons Attribution-NonCommercial 4.0 International** licence (CC BY-NC 4.0,
<https://creativecommons.org/licenses/by-nc/4.0/>), © 2026 Matteo Guardamagna:

- the corpus: `data/units/`, `stimuli/`, `data/processed/units.csv`, `data/processed/stimuli.csv`;
- the run records and outputs: `data/processed/`, `outputs/`;
- the encoding-model predictions: `data/tribe/MANIFEST.sha256` and the release bundle
  `neurotutorsim_tribe_d3_<date>.zip`.

The non-commercial condition follows from the encoding model. The predicted cortical responses were produced with
TRIBE v2 (d'Ascoli et al., 2026; <https://github.com/facebookresearch/tribev2>), whose code and weights are released
under CC BY-NC 4.0, and which encodes text with Llama 3.2 3B under the Llama 3.2 Community License
(<https://www.llama.com/llama3_2/license/>). The choices of the hybrid runs, summarised in `outputs/`, were produced
with Centaur (Binz et al., 2025), a fine-tuned Llama 3.1 model under the Llama 3.1 Community License, and the tutor
turns with Qwen2.5-3B-Instruct under the Qwen Research License. No model weights are distributed here.

Cite the report or this repository when reusing the data.
