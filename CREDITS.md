# Credits

## 3D muscle model (`models/muscles.glb`)

`models/muscles.glb` is used unmodified from
[kalibismail/hoik-muscle-model](https://github.com/kalibismail/hoik-muscle-model),
which adapted it from:

- **Z-Anatomy — The libre 3D atlas of anatomy**, by Gauthier Kervyn
  (<https://github.com/Z-Anatomy/Models-of-human-anatomy>), licensed
  [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/).
- **BodyParts3D**, © The Database Center for Life Science (Kousaku Okubo),
  licensed [CC BY-SA 2.1 Japan](https://creativecommons.org/licenses/by-sa/2.1/jp/).

That repository's modifications: muscle meshes were selected and grouped into
44 regions, decimated, given baked ambient occlusion, and their textures and
original materials were removed. See its README for the full list.

The model file is distributed here under **CC BY-SA 4.0**. EZRep recolors the
model at runtime; the file itself is unchanged.

## Libraries

- [three.js](https://threejs.org) (MIT), loaded from jsDelivr.
- [PyScript](https://pyscript.net) / MicroPython (Apache 2.0 / MIT), loaded from pyscript.net.
