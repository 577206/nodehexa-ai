"""Visual and control-contract checks. POST endpoints are intercepted, never sent."""
from pathlib import Path
import json, time
from playwright.sync_api import sync_playwright, expect

OUT=Path(__file__).resolve().parent
URL='http://127.0.0.1:8765/studio'

def main():
    errors=[]; requests=[]; failures=[]; result={}
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True,executable_path='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome')
        page=browser.new_page(viewport={'width':1440,'height':1000},reduced_motion='reduce')
        page.on('pageerror',lambda error:errors.append(str(error)))
        # Read current status only; all mutations are blocked during real-state review.
        def intercept_mutation(route):
            if route.request.method=='POST':
                failures.append('Unexpected real POST '+route.request.url)
                route.abort()
            else:route.continue_()
        page.route('**/api/**',intercept_mutation)
        page.goto(URL);page.wait_for_load_state('networkidle')
        expect(page.locator('#connection')).to_have_text('工作台未连接')
        expect(page.locator('[data-theater]').first).to_be_disabled()
        expect(page.locator('#stop')).to_be_enabled()
        assert page.locator('[data-theater]').count()==3
        assert page.locator('[data-eye]').count()==5
        assert page.locator('[data-motion]').count()==4
        # Load every lazy image before checking its bytes and capturing full-page output.
        for img in page.locator('img').all():
            img.scroll_into_view_if_needed()
            expect(img).to_have_js_property('complete',True)
            assert img.evaluate('(i)=>i.naturalWidth>0'),img.get_attribute('src')
        for width in [1440,1024,768,700,390,320]:
            page.set_viewport_size({'width':width,'height':1000 if width>700 else 844})
            assert page.evaluate('document.documentElement.scrollWidth<=innerWidth'),f'Overflow at {width}'
        # A fresh surface avoids Chromium stale compositor tiles after repeated resizes.
        page.close()
        page=browser.new_page(viewport={'width':1440,'height':1000},reduced_motion='reduce')
        page.on('pageerror',lambda error:errors.append(str(error)))
        page.route('**/api/**',intercept_mutation)
        page.goto(URL);page.wait_for_load_state('networkidle');page.evaluate('document.fonts.ready')
        page.screenshot(path=str(OUT/'v2-desktop-preview.png'))
        page.screenshot(path=str(OUT/'v2-desktop-full.png'),full_page=True)
        page.locator('#actions').screenshot(path=str(OUT/'v2-actions-preview.png'))
        page.locator('#studio').screenshot(path=str(OUT/'v2-console-preview.png'))
        mobile=browser.new_page(viewport={'width':390,'height':844},reduced_motion='reduce')
        mobile.route('**/api/**',intercept_mutation)
        mobile.on('pageerror',lambda error:errors.append(str(error)))
        mobile.goto(URL);mobile.wait_for_load_state('networkidle');mobile.evaluate('document.fonts.ready')
        mobile.screenshot(path=str(OUT/'v2-mobile-preview.png'))
        for img in mobile.locator('img').all():img.scroll_into_view_if_needed()
        mobile.screenshot(path=str(OUT/'v2-mobile-full.png'),full_page=True)
        media=page.request.get('http://127.0.0.1:8765/studio-media/actions_r03/unique_actions_reel.mp4')
        assert media.ok and len(media.body())>1000
        result['offline_and_responsive']='pass';result['widths']=[1440,1024,768,700,390,320]
        # A separate context mocks every API call to exercise the existing UI contracts.
        mock=browser.new_page(viewport={'width':1440,'height':1000},reduced_motion='reduce')
        mock.on('pageerror',lambda error:errors.append(str(error)))
        state={'online':True,'motion':False,'fail':False}
        def api(route):
            req=route.request; endpoint=req.url.split('/api/')[-1]
            if req.method=='GET':
                route.fulfill(json={'boardOnline':state['online'],'motionEnabled':state['motion'],'theater':{'state':'idle'}})
                return
            body=req.post_data_json;requests.append({'endpoint':endpoint,'body':body})
            if state['fail']:
                state['fail']=False;route.fulfill(status=409,json={'error':'动作被拒绝，请检查状态'});return
            if endpoint=='motion-enable':state['motion']=body['enabled']
            if endpoint=='stop':state['motion']=False
            route.fulfill(json={'message':'已接受测试指令','enabled':state['motion']})
        mock.route('**/api/**',api)
        mock.goto(URL);expect(mock.locator('#connection')).to_have_text('工作台已连接')
        for selector in ['[data-theater]','[data-eye]','[data-motion]']:
            for button in mock.locator(selector).all():
                expect(button).to_be_enabled();button.click();expect(button).to_be_enabled()
        mock.locator('#motion-enabled').check();expect(mock.locator('#motion-enabled')).to_be_checked()
        mock.locator('#stop').click();expect(mock.locator('#motion-enabled')).not_to_be_checked()
        state['fail']=True;mock.locator('[data-motion]').first.click()
        expect(mock.locator('#receipt')).to_have_text('动作被拒绝，请检查状态')
        assert [r['body']['action'] for r in requests if r['endpoint']=='theater']==['hold_that_compliment','gossip_radar','compliment_receipt']
        assert [r['body']['mode'] for r in requests if r['endpoint']=='eyes']==[11,4,5,7,-1]
        assert all(r['body']['durationMs']==5000 and r['body']['contrast']==127 for r in requests if r['endpoint']=='eyes')
        assert [r['body']['action'] for r in requests if r['endpoint']=='motion'][:4]==['rotate_x','rotate_z','twist','beat_sway']
        assert any(r['endpoint']=='stop' and r['body']=={} for r in requests)
        assert not errors,errors
        assert not failures,failures
        result.update({'mocked_control_contract':'pass','post_requests_mocked':len(requests),'real_post_requests':0,'javascript_errors':errors,'failures':failures,'video_http':'pass','visual_status':'preview_awaiting_user_feedback'})
        browser.close()
    (OUT/'v2-validation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(result,ensure_ascii=False))

if __name__=='__main__':main()
