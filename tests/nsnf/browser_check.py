"""Run against the local API; real browser controls, no network stubs."""
from pathlib import Path
import json
from io import BytesIO
import wave
import numpy as np
from playwright.sync_api import sync_playwright

root=Path(__file__).resolve().parents[2] / 'evidence' / 'nsnf'
with sync_playwright() as p:
    browser=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
    page=browser.new_page(viewport={'width':1440,'height':1100})
    errors=[]
    page.on('pageerror',lambda error:errors.append(str(error)))
    page.goto('http://127.0.0.1:8765/')
    page.get_by_text('Connected to local field',exact=True).wait_for()
    assert page.locator('.slot').count()==320
    page.get_by_role('button',name='Execute field',exact=True).click()
    page.get_by_text('5 active · tier 1',exact=True).wait_for()
    assert page.locator('.slot.active').count()==5
    page.get_by_role('button',name='Verify replay',exact=True).click()
    page.get_by_text('Exact replay verified against stored neural outputs.',exact=True).wait_for()
    page.screenshot(path=str(root/'field-desktop.png'),full_page=True)
    page.get_by_text('Submit a contact observation',exact=True).click()
    page.get_by_role('button',name='Investigate contact',exact=True).click()
    page.get_by_text('What did this contact mean in this situation?',exact=True).wait_for()
    assert 'request_clarification' in page.locator('#output').inner_text()
    page.get_by_role('button',name='Save checkpoint',exact=True).click()
    page.wait_for_function("document.querySelector('#notice').textContent.startsWith('Saved checkpoint')")
    page.reload()
    page.wait_for_function("document.querySelectorAll('#history button').length>0")
    page.locator('#history button').first.click()
    assert page.locator('.slot.active').count()>0
    page.set_viewport_size({'width':390,'height':844})
    assert page.evaluate('document.documentElement.scrollWidth<=window.innerWidth')
    page.screenshot(path=str(root/'field-mobile.png'),full_page=True)
    page.get_by_text('Analyze real audio',exact=True).click()
    stream=BytesIO()
    with wave.open(stream,'wb') as wav:
        wav.setnchannels(1);wav.setsampwidth(2);wav.setframerate(16000)
        wav.writeframes((np.sin(2*np.pi*200*np.arange(16000)/16000)*12000).astype('<i2').tobytes())
    page.locator('#audio-file').set_input_files({'name':'measured-tone.wav','mimeType':'audio/wav','buffer':stream.getvalue()})
    page.get_by_role('button',name='Analyze audio',exact=True).click()
    page.get_by_text('Audio measured and persisted. Meaning remains unresolved.',exact=True).wait_for()
    page.locator('audio').wait_for()
    assert 'candidate_f0_hz' in page.locator('#output').inner_text()
    assert page.evaluate('document.documentElement.scrollWidth<=window.innerWidth')
    page.screenshot(path=str(root/'audio-mobile.png'),full_page=True)
    assert not errors, errors
    (root/'browser-results.json').write_text(json.dumps({'passed':True,'slots':320,'desktop':[1440,1100],
        'mobile':[390,844],'checks':['execution','active slots','exact replay','nonverbal clarification','checkpoint','history after reload','no horizontal overflow','no page errors','real WAV upload','playback URL','acoustic evidence retrieval'],
        'method':'Playwright Chromium; Browser plugin tool unavailable'},indent=2))
    browser.close()
