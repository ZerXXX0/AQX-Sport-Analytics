"""Optional browser checks against the actual running app (requires Playwright).

Run from the repository root: python visualization/check_browser.py
Screenshots are written to ignored data/visualization-checks/.
"""
import argparse
import html
import sys
from pathlib import Path

import joblib
import pandas as pd
from playwright.sync_api import expect, sync_playwright

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from charts import prepare_chart_data
from core import FEATURES, ROOT


IFRAME = 'iframe[title="charts.clutchiq_shot_explorer"]'


def start(page, url):
    page.goto(url, wait_until='domcontentloaded')
    page.get_by_role('tab', name='Shot Explorer', exact=True).wait_for(state='attached', timeout=60000)
    if page.viewport_size['width'] <= 760:
        # The latest frontend explicitly expands the sidebar on first load.
        close_sidebar = page.locator('[data-testid="stSidebarCollapseButton"] button')
        if close_sidebar.is_visible():
            close_sidebar.click()
    page.get_by_role('tab', name='Shot Explorer', exact=True).click(timeout=60000)
    frame = page.frame_locator(IFRAME)
    expect(frame.locator('#content')).to_be_visible(timeout=60000)
    expect(frame.locator('#error')).to_be_hidden()
    return frame


def check_geometry(frame):
    bounds = frame.locator('#court').bounding_box()
    assert abs(bounds['width'] / bounds['height'] - 54 / 51) < .002
    assert frame.locator('body').evaluate('(el) => el.scrollWidth <= innerWidth + 1')


def send_packet(page, packet):
    page.evaluate('''packet => document.querySelector('iframe[title="charts.clutchiq_shot_explorer"]')
      .contentWindow.postMessage({type:'streamlit:render', args:{packet}}, '*')''', packet)


def main(url):
    data = pd.read_parquet(ROOT / 'data/shots.parquet')
    out = ROOT / 'data/visualization-checks'
    out.mkdir(exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        errors = []
        page = browser.new_page(viewport={'width': 1440, 'height': 1100})
        page.on('pageerror', lambda error: errors.append(str(error)))
        page.on('console', lambda message: errors.append(message.text) if message.type == 'error' else None)
        frame = start(page, url)
        component_src = page.locator(IFRAME).get_attribute('src')
        expect(frame.locator('#stats')).to_contain_text(f'{len(data):,}')
        expect(frame.locator('#coverage')).to_contain_text('435 outside')
        check_geometry(frame)
        frame.get_by_text('Hexbin heatmap', exact=True).click()
        frame.locator('#metric').select_option('fg')
        frame.locator('.hex[data-cell="0,0"]').click()
        expect(frame.locator('#selection-title')).to_have_text('Area 0,0')
        expect(frame.locator('.hex[data-cell="0,0"]')).to_have_attribute('aria-pressed', 'true')
        frame.locator('#threshold').focus()
        frame.locator('#threshold').press('End')
        expect(frame.locator('#threshold-value')).to_have_text('250')
        assert frame.locator('.hex[fill-opacity="0.36"]').count() > 0
        cell_id = frame.locator('.hex[fill-opacity="0.36"]').evaluate_all('''els => els.find(el => {
          const [x,y] = CourtMath.hexCenter(el.dataset.cell, 2);
          return Math.abs(x) < 22 && y > 0 && y < 38;
        }).dataset.cell''')
        target = frame.locator(f'.hex[data-cell="{cell_id}"]')
        target.hover()
        expect(frame.locator('#tooltip')).to_be_visible()
        expect(frame.locator('#tooltip')).to_contain_text('sampel belum mencukupi')
        tooltip = frame.locator('#tooltip').bounding_box()
        assert tooltip['x'] >= 0 and tooltip['y'] >= 0
        assert tooltip['x'] + tooltip['width'] <= 1441
        assert tooltip['y'] + tooltip['height'] <= 1101
        target.focus()
        target.press('ArrowRight')
        focused = frame.locator('.hex:focus')
        focused_id = focused.get_attribute('data-cell')
        focused.press('Enter')
        expect(frame.locator('#selection-title')).to_have_text(f'Area {focused_id}')
        frame.locator('#clear').click()
        expect(frame.locator('#selection-title')).to_have_text('All zones')
        frame.get_by_text('Scatter shots', exact=True).click()
        frame.locator('#shot-surface').focus()
        frame.locator('#shot-surface').press('End')
        frame.locator('#shot-surface').press('Enter')
        expect(frame.locator('#shot-detail')).to_be_visible()
        assert frame.locator('#highlight circle').count() > 0
        frame.locator('#shot-surface').press('Escape')
        expect(frame.locator('#clear')).to_be_disabled()
        frame.locator('.modes').get_by_text('Expected points', exact=True).click()
        expect(frame.locator('#prediction-status')).to_contain_text('unavailable')
        expect(frame.locator('#court-empty')).to_be_visible()
        print('PASS desktop modes, selection/reset, threshold, tooltip, keyboard, unavailable overlay', flush=True)

        # Existing sidebar integrations must still drive the exact same data.
        page.get_by_role('combobox').nth(0).click()
        page.get_by_role('option', name='Atlanta Hawks', exact=True).click()
        team = data[data.TEAM_NAME.eq('Atlanta Hawks')]
        expect(frame.locator('#stats')).to_contain_text(f'{len(team):,}', timeout=30000)
        page.get_by_role('combobox').nth(1).fill('Trae Young')
        page.get_by_role('option', name='Trae Young', exact=True).click()
        player = data[data.PLAYER_NAME.eq('Trae Young')]
        expect(frame.locator('#stats')).to_contain_text(f'{len(player):,}', timeout=30000)
        frame.get_by_text('Hexbin heatmap', exact=True).click()
        frame.locator('#metric').select_option('fg')
        frame.locator('#court-wrap').screenshot(path=str(out / 'desktop-court.png'))
        frame.locator('#explorer').screenshot(path=str(out / 'desktop.png'))
        for width in (1024, 768):
            page.set_viewport_size({'width': width, 'height': 1100})
            check_geometry(frame)
        print('PASS actual player filter and desktop/tablet aspect ratio', flush=True)

        mobile = browser.new_context(viewport={'width': 390, 'height': 844}, is_mobile=True, has_touch=True, device_scale_factor=1)
        phone = mobile.new_page()
        phone.on('pageerror', lambda error: errors.append(str(error)))
        phone.on('console', lambda message: errors.append(message.text) if message.type == 'error' else None)
        mf = start(phone, url)
        check_geometry(mf)
        # Inspect an actual shot with a touch event at its true position.
        mf.locator('#zone').select_option(label='Restricted Area')
        surface = mf.locator('#shot-surface').bounding_box()
        actual = data[data.SHOT_ZONE_BASIC.eq('Restricted Area')].iloc[0]
        mf.locator('#shot-surface').tap(position={
            'x': (actual.LOC_X / 10 + 25) * surface['width'] / 50,
            'y': (41.75 - actual.LOC_Y / 10) * surface['height'] / 47,
        })
        expect(mf.locator('#shot-detail')).to_be_visible()
        # A hexbin tap has a persistent inspector, independent of hover.
        mf.get_by_text('Hexbin heatmap', exact=True).tap()
        mf.locator('.hex[data-cell="0,0"]').tap()
        expect(mf.locator('#selection-title')).to_have_text('Area 0,0')
        mf.locator('#clear').tap()
        expect(mf.locator('#selection-title')).to_have_text('All zones')
        mf.locator('#zone').select_option(label='Backcourt')
        expect(mf.locator('#court-empty')).to_contain_text('No mapped shots')
        expect(mf.locator('#stats')).to_contain_text(f'{len(data[data.SHOT_ZONE_BASIC.eq("Backcourt")]):,}')
        mf.locator('#zone').select_option(label='Restricted Area')
        mf.locator('#explorer').screenshot(path=str(out / 'mobile.png'))
        phone.set_viewport_size({'width': 320, 'height': 844})
        check_geometry(mf)
        print('PASS mobile/touch selection, off-court empty state, 320px without overflow', flush=True)

        # Exercise available probabilities with actual predictions from the
        # unchanged saved model. This affects only the browser test session.
        scored = player.head(300).copy()
        model = joblib.load(ROOT / 'artifacts/model.joblib')
        scored['predicted_probability'] = model.predict_proba(scored[FEATURES])[:, 1]
        packet = prepare_chart_data(scored)
        # An isolated parent harness avoids Streamlit's authoritative rerenders
        # replacing the scored test packet with the real unscored Parquet.
        harness = '''<!doctype html><html><head><meta name="viewport" content="width=device-width,initial-scale=1">
          <style>body{margin:0;background:#0b1020}iframe{width:100%;border:0}</style></head><body>
          <iframe title="charts.clutchiq_shot_explorer" src="''' + html.escape(component_src, quote=True) + '''"></iframe>
          <script>addEventListener('message',e=>{
            const f=document.querySelector('iframe');if(e.source!==f.contentWindow)return;
            if(e.data.type==='streamlit:componentReady')window.componentReady=true;
            if(e.data.type==='streamlit:setFrameHeight')f.style.height=e.data.height+'px';
          });</script></body></html>'''
        phone.route('**/__visualization_test__', lambda route: route.fulfill(content_type='text/html', body=harness))
        phone.goto(url.rstrip('/') + '/__visualization_test__')
        phone.wait_for_function('window.componentReady === true')
        mf = phone.frame_locator(IFRAME)
        send_packet(phone, packet)
        expect(mf.locator('#stats')).to_contain_text('300')
        mf.locator('.modes').get_by_text('Expected points', exact=True).tap()
        expected = (scored.predicted_probability * scored.shot_value).mean()
        expect(mf.locator('#stats')).to_contain_text(f'{expected:.2f}')
        expect(mf.locator('#court-empty')).to_be_hidden()
        expect(mf.locator('#prediction-status')).to_contain_text('300 of 300')
        send_packet(phone, prepare_chart_data(scored.iloc[:0]))
        expect(mf.locator('#court-empty')).to_be_visible()
        send_packet(phone, {'rows': None, 'court': packet['court']})
        expect(mf.locator('#error')).to_be_visible()
        send_packet(phone, packet)
        expect(mf.locator('#content')).to_be_visible()
        phone.screenshot(path=str(out / 'mobile-expected-points.png'), full_page=True)
        assert errors == [], errors
        print('PASS actual model probabilities/expected points, empty/error recovery; no page or console errors', flush=True)
        browser.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--url', default='http://127.0.0.1:8502')
    main(parser.parse_args().url)
