import sys, tempfile, pathlib, json, asyncio, io
# Run with the project's installed Python environment. All test data is temporary.
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3] / 'backend'))
import config
root=pathlib.Path(tempfile.mkdtemp(prefix='ttp-audit-'))
for key, sub in [('DATABASE_DIR','db'),('ARTIFACTS_DIR','artifacts'),('REGISTRY_DIR','registry')]:
 p=root/sub;p.mkdir();setattr(config,key,p)
config.DB_PATH=config.DATABASE_DIR/'audit.db'
from db.database import init_db,get_db_connection
from db import repository
init_db()
from api.routers.experiments import DecisionRecordSchema
from api.routers.runs import LaunchRunSchema
from pydantic import ValidationError
try: DecisionRecordSchema(run_id='r1',status='SELECTED',decision_rationale='reason')
except ValidationError as e: print('UI decision payload rejected:',[(x['loc'],x['type']) for x in e.errors()])
print('Blank/invalid decision accepted:',DecisionRecordSchema(run_id='r1',status='INVALID',rationale='').model_dump())
p=LaunchRunSchema(run_id='../outside',experiment_id='e1',approach_name='x',epochs=0,batch_size=-1,learning_rate=-1,motivating_reason='important')
print('Invalid launch accepted; motivation dropped:',p.model_dump())
c=get_db_connection();repository.create_experiment(c,'e1','audit','objective')
for r in ['r1','r2']: repository.create_run(c,r,'e1','a','custom_cnn',2,1,.001,42,status='FAILED')
c.close()
from registry.model_registry import ModelRegistry
reg=ModelRegistry();print('Missing checkpoint, FAILED, no decision promotion:',reg.promote_candidate('audit','r1'))
(config.ARTIFACTS_DIR/'r1_best_checkpoint.pt').write_bytes(b'run-one')
reg.promote_candidate('collision','r1')
(config.ARTIFACTS_DIR/'r2_best_checkpoint.pt').write_bytes(b'run-two')
reg.promote_candidate('collision','r2')
c=get_db_connection();row=dict(c.execute("select * from models where name='collision'").fetchone());c.close()
print('Version collision recorded run:',row['run_id'],'artifact bytes:',pathlib.Path(row['checkpoint_path']).read_bytes())
from core.models import get_model_by_name
print('CustomCNN parameters:',sum(p.numel() for p in get_model_by_name('custom_cnn').parameters()))
from core.dataset import get_transforms
from PIL import Image
print('64x64 transform output:',tuple(get_transforms(False)(Image.new('RGB',(64,64))).shape))
from api.routers.inference import predict_image
from starlette.datastructures import UploadFile,Headers
b=io.BytesIO();Image.new('RGB',(32,32)).save(b,format='PNG');b.seek(0)
r=asyncio.run(predict_image(UploadFile(file=b,filename='audit.png',headers=Headers({'content-type':'image/png'})),model_name='custom_cnn',run_id='missing'))
print('Missing checkpoint inference returned:',r['predicted_class'],r['confidence_score'])
print('All probe writes isolated in:',root)
from torch.utils.data import DataLoader,TensorDataset
import torch
from core.trainer import Trainer
x=torch.rand(4,3,32,32);y=torch.tensor([0,1,2,3]);loader=DataLoader(TensorDataset(x,y),batch_size=2)
t=Trainer(get_model_by_name('custom_cnn'),loader,loader,device=torch.device('cpu'),save_dir=config.ARTIFACTS_DIR)
h=t.train(1,run_id='synthetic_smoke')
print('Synthetic trainer smoke:',len(h['train_loss']),'epoch; checkpoint exists:',bool(h['best_checkpoint_path'] and pathlib.Path(h['best_checkpoint_path']).exists()))
