import os,sys,subprocess,tempfile,json,unittest
from pathlib import Path
from PIL import Image,ImageDraw
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT/'tools/blender'))
from painted_relief import build_mesh


class PaintedIntegration(unittest.TestCase):
    def test_live_finish_and_actual_obj(self):
        if not os.environ.get('BLENDER_EXECUTABLE'):
            if os.environ.get('BLENDER_TESTS_REQUIRED')=='1':self.fail('pinned Blender required')
            self.skipTest('BLENDER_EXECUTABLE not configured')
        with tempfile.TemporaryDirectory() as folder:
            image=Path(folder)/'painted.png';data=Image.new('RGBA',(65,65),(0,0,0,0))
            ImageDraw.Draw(data).ellipse((4,4,60,60),fill=(230,160,80,252));data.save(image)
            mesh=Path(folder)/'mesh.json';mesh.write_text(json.dumps(build_mesh(image,grid=24)))
            result=subprocess.run([sys.executable,'tools/blender/run.py','tools/blender/tests/painted_relief_blender.py','--',str(mesh),str(image)],cwd=ROOT,capture_output=True,text=True,encoding='utf-8')
            self.assertEqual(result.returncode,0,result.stdout+'\n'+result.stderr)
            self.assertIn('PAINTED RELIEF BLENDER OK',result.stdout)


if __name__=='__main__':unittest.main()
