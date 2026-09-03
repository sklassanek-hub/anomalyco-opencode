import json

p = 'config.json'
c = json.load(open(p, encoding='utf-8'))
c['sources']['vk']['token'] = 'vk1.a.DWSVVTl2Y6hbe-ggT9WRsiiCHadm0NgH5NJdCDaOp4R1Puam3I8d_ohC5gjfa_Rq9jOjsZj8tMbQpU_Sdz4HmwZLXU16F5MP0rZ0ekoPCvC2wzPFn2QLLT8JSLxH0eEm9vC2hj6uSIfzk3lqkkRMfYVGvWoGDc3dE22zdZyQIIllRz3gyKpXh3F7yUnIO5G3qJmbUbuNq8Ow1t-9q1e9Ag'
json.dump(c, open('config.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('VK token updated')