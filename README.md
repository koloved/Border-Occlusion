
# BorderOcclusion

**BorderOcclusion** is a Blender 4.5+ add-on for selective mesh element picking using customizable mouse gestures. It enables advanced selection workflows for faces, vertices, and edges in dense geometry—such as backface-only vertex selection—directly through drag operations with modifier keys.

## Features

- **Customizable Drag Selection**: Assign mouse gestures (Shift/Ctrl/Alt) for different selection behaviors.
- **Backface-Only Selection**: Drag-select only vertices, edges, or faces whose normals face away from the camera.
- **Extend/Deselect Handling**: Easily add to or remove from selections using modifier keys.
- **Selection Consistency**: Uses modal operator logic and BMesh selection flush to prevent Blender’s automatic selection propagation to unwanted element types.
- **Preference Panel**: Choose UI icon position and visualize current keymap/hotkey bindings.


## Installation

1. Download or clone this repository.
2. In Blender, go to **Edit > Preferences > Add-ons > Install**, and select the `.py` file.
3. Enable the add-on (“BorderOcclusion”) in the Add-on list.
4. Configure preferences via **Edit > Preferences > Add-ons > BorderOcclusion**.

## Usage

1. In *Edit Mode*, select faces, vertices, or edges.
2. Drag with the **Right Mouse Button** using the following modifiers:
    - **Ctrl+Alt+Shift**: **Backface Only** selection. Selects only geometry facing away from the camera (e.g., to pick vertices hidden behind dense front geometry).
    - **Ctrl**: **Extend** selection (adds to selection).
3. Switch between Vertex/Edge/Face selection using Blender’s default controls.
4. The tool automatically prevents unwanted face selection when switching modes, so backface-only vertex/edge selections don't promote front-facing faces.

## Default Hotkeys

| Mouse Drag | Shift | Ctrl | Alt | Action |
| :--: | :--: | :--: | :--: | :-- |
| Right Mouse |  | ✓ |  | Extend Selection |
| Right Mouse | ✓ | ✓ | ✓ | Backface Only |

*You can further customize hotkeys in the Blender Preferences Add-on panel.*

## Advanced Functionality

- Custom icon menu location: Choose left/right/none for workflow integration.
- Conflict detection for hotkeys: Find clashes with other add-ons or Blender functions.
- Uses Blender’s BMesh API for robust geometry detection and selection consistency.


## Compatibility

- Requires **Blender 4.5+** (uses latest API conventions for properties, BMesh, and modal operators).
- Supports Windows, Linux, and macOS versions of Blender.


## Development

Contributions, bug reports, and feature suggestions are welcome! See the `issues` tab or create a PR.
