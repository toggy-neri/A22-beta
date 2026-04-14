from gradio_client import Client, handle_file

client = Client("https://damo-xr-lab-lam-large-avatar-model.ms.show/")
result = client.predict(
		input_image=handle_file('xjpic.jpg'),
		api_name="/assert_input_image"
)
print(result)