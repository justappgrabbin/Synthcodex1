from pathlib import Path
from tempfile import TemporaryDirectory
import os, subprocess, sys, time, urllib.request, json
from playwright.sync_api import sync_playwright
root=Path(__file__).resolve().parents[2]
with TemporaryDirectory() as data:
 env={**os.environ,'NSNF_DATA':data}
 server=subprocess.Popen([sys.executable,'-m','uvicorn','api.server:create_app','--factory','--host','127.0.0.1','--port','8877'],cwd=root,env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
 try:
  for _ in range(100):
   try:
    urllib.request.urlopen('http://127.0.0.1:8877/health');break
   except OSError:time.sleep(.05)
  else:raise RuntimeError('API did not start')
  with sync_playwright() as p:
   browser=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
   page=browser.new_page(viewport={'width':1440,'height':1100})
   errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
   page.goto('http://127.0.0.1:8877/')
   page.get_by_role('button',name='Execute field',exact=True).click()
   page.get_by_text('Perception — D3: not yet perceptible · D4: not yet perceptible · D5: not yet perceptible',exact=True).wait_for()
   edges=[{'src':a,'dst':b,'type':'neural-state','weight':.5,'rule_version':'browser-test-v1','evidence_ref':'browser-test','disposition':'ENGINEERING HYPOTHESIS'} for a,b in [('d0:g0','d1:g0'),('d1:g0','d2:g0')]]
   assert page.request.post('http://127.0.0.1:8877/topology',data=edges).ok
   result=page.request.post('http://127.0.0.1:8877/execute',data={'features':[1,0,0,0,0,0,0,0],'tier':3,'candidates':[0,64,128]})
   assert result.ok
   page.reload();page.locator('#history button').first.wait_for();page.locator('#history button').first.click()
   page.get_by_text('Perception — D3: perceptible · D4: not yet perceptible · D5: not yet perceptible',exact=True).wait_for()
   assert 'three-dimensions-including-current-v1' in page.locator('#output').inner_text()
   page.get_by_role('button',name='Verify replay',exact=True).click()
   page.get_by_text('Exact replay verified against stored neural outputs.',exact=True).wait_for()
   page.screenshot(path='/tmp/perception-desktop.png',full_page=True)
   page.set_viewport_size({'width':390,'height':844})
   assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
   page.screenshot(path='/tmp/perception-mobile.png',full_page=True)
   assert not errors,errors
   (root/'evidence/nsnf/perception-browser.json').write_text(json.dumps({'passed':True,'checks':['blocked perception shown','accepted three-dimension perception shown','current dimension counted','trace version shown','perception replay verified','mobile no overflow','no JS errors'],'desktop':[1440,1100],'mobile':[390,844],'method':'Playwright Chromium'},indent=2))
   browser.close()
 finally:
  server.terminate();server.wait(timeout=10)
