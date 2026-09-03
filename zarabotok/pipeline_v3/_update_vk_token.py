import json

p = 'config.json'
c = json.load(open(p, encoding='utf-8'))
c['sources']['vk']['token'] = 'vk1.a.Eebf_qS2NgC9_TBn-OuLpGCmXd3qP7myxIASSa1fZclJntHC48WSYHwhMwaX3bu5gU48t3Gpb5kOc-r7G5kvcZZVZPX3iz1_JeKtmt1Y3VtQ_2s-qAd3E0Noo8SDBYGZ3yC'
json.dump(c, open('config.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('VK token updated')