import json
from channels.generic.websocket import AsyncWebsocketConsumer

class TaskStatusConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.record_id = self.scope['url_route']['kwargs']['record_id'] 
        self.group_name = f"task_{self.record_id}" 

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive(self, text_data):
        pass  

    async def task_status_update(self, event):
        await self.send(text_data=json.dumps(event["message"]))

from channels.generic.websocket import AsyncWebsocketConsumer
import json

class DatasetStatusConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.dataset_id = self.scope['url_route']['kwargs']['dataset_id']
        self.room_group_name = f'dataset_{self.dataset_id}'
        
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )


    async def receive(self, text_data):
        pass

    async def status_update(self, event):
        await self.send(text_data=json.dumps({
            'type': 'status_update',
            'dataset_id': event['dataset_id'],
            'status': event['status'],
            'message': event.get('message', '')
        }))