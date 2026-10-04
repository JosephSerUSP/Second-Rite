"""Fail before rendering when an editable source cannot resolve its dependencies."""
from pathlib import Path


def assert_available():
    import bpy
    missing=[];images=[]
    for image in bpy.data.images:
        if not image.users or image.source not in ('FILE','TILED'):
            continue
        packed=bool(image.packed_file or image.packed_files)
        path=Path(bpy.path.abspath(image.filepath,library=image.library))
        if image.source=='TILED':
            raise ValueError(f'UDIM dependency validation is unsupported: {image.name}')
        if not packed and not path.is_file(): missing.append(f'{image.name}: {path}')
        images.append(dict(name=image.name,path=str(path),packed=packed))
    for library in bpy.data.libraries:
        path=Path(bpy.path.abspath(library.filepath))
        if not path.is_file(): missing.append(f'Linked library: {path}')
    if missing:
        raise ValueError('Source dependencies missing; refusing invalid beauty render:\n'+'\n'.join(missing))
    return images
