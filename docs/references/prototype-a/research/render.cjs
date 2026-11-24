const {chromium} = require(process.env.LEAGUESTATS_PLAYWRIGHT || '/tmp/leagueStats-web-validation.Pj3GOO/node_modules/playwright');
const fs = require('node:fs');
const path = require('node:path');
const assert = require('node:assert/strict');
const {pathToFileURL} = require('node:url');
const http = require('node:http');
const base = path.resolve(__dirname,'..');
const url = pathToFileURL(path.join(base,'prototype.html')).href;
const metrics = {};
const errors = [];

function getPageURL(direction, screen, extra) {
  return url + '?' + new URLSearchParams({direction,screen,...extra});
}
async function go(page, direction, screen, extra) {
  await page.goto(getPageURL(direction,screen,extra));
  await page.locator('main').waitFor();
  await page.evaluate(async () => {
    await document.fonts.ready;
    await Promise.all([...document.images].map(image => image.decode()));
  });
}
async function save(page, name, fullPage = false) {
  await page.screenshot({path:path.join(base,'images',name+'.png'), animations:'disabled',fullPage});
  metrics[name] = await page.evaluate(() => {
    function position(selector) {
      const element = document.querySelector(selector);
      if (!element) return null;
      const r = element.getBoundingClientRect();
      return {y:Math.round(r.top+scrollY),h:Math.round(r.height),end:Math.round(r.bottom+scrollY)};
    }
    const clipped = [...document.querySelectorAll('h1,h2,h3,p,strong,small,.field-value span,.roles a,.metrics dt,.metrics dd,button')]
      .filter(el=>el.clientWidth && el.scrollWidth>el.clientWidth+3).map(el=>el.textContent.trim().slice(0,90));
    return {
      viewport:[innerWidth,innerHeight], doc:[document.documentElement.scrollWidth,document.documentElement.scrollHeight],
      scrollY, clipped, fonts:[...document.fonts].filter(font=>font.status==='loaded').map(font=>font.family + ' ' + font.weight),
      homeCta:position('.setup button'), canonical:position('.canonical,.pick-brief'),
      firstAlternative:position('.canonical+.ranked-row,.choice-row'),
      alternativesFullyVisible:[...document.querySelectorAll('.ranked-row:not(.canonical),.choice-row')].filter(el=>{
        const r=el.getBoundingClientRect();
        return r.top>=0 && r.bottom<=innerHeight;
      }).length,
      bans:position('.bans'), lineup:position('.lineup'), draftEntry:position('.draft-title,.view-nav a:last-child,.quick-jumps a')
    };
  });
}
async function zoomText(page) {
  await page.evaluate(() => {
    const candidates = [...document.querySelectorAll('body *')].filter(el=>el instanceof HTMLElement && getComputedStyle(el).display!=='none');
    const computed = candidates.map(el => [el, parseFloat(getComputedStyle(el).fontSize)]);
    for (const [el,size] of computed) el.style.fontSize = (size*2)+'px';
  });
}
async function nativeZoom() {
  const types = {'.html':'text/html','.js':'text/javascript','.css':'text/css','.woff2':'font/woff2','.webp':'image/webp'};
  const server = http.createServer((request,response) => {
    const pathname = new URL(request.url,'http://127.0.0.1').pathname;
    const filename = path.resolve(base,'.'+pathname);
    if (!filename.startsWith(base+path.sep) || !fs.existsSync(filename) || !types[path.extname(filename)]) {
      response.writeHead(404).end();
      return;
    }
    response.writeHead(200,{'Content-Type':types[path.extname(filename)]});
    fs.createReadStream(filename).pipe(response);
  });
  await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
  const origin = 'http://127.0.0.1:'+server.address().port;
  const ext = path.join(__dirname,'zoom-extension');
  let context;
  try {
    context = await chromium.launchPersistentContext('',{channel:'chromium',viewport:{width:1366,height:768},
      deviceScaleFactor:1,args:['--disable-extensions-except='+ext,'--load-extension='+ext]});
    const page = context.pages()[0];
    const worker = context.serviceWorkers()[0] || await context.waitForEvent('serviceworker');
    for (const screen of ['home','solo','team']) {
      const pageUrl = origin+'/prototype.html?direction=a&screen='+screen;
      await page.goto(pageUrl);
      const zoom = await worker.evaluate(async url => {
        const tab = (await chrome.tabs.query({})).find(t=>t.url===url);
        await chrome.tabs.setZoom(tab.id,2);
        return chrome.tabs.getZoom(tab.id);
      },pageUrl);
      assert.equal(zoom,2);
      await page.waitForFunction(()=>innerWidth===683);
      await page.evaluate(()=>document.fonts.ready);
      await save(page,'a-native-zoom-200-'+screen+'-1366x768');
    }
  } finally {
    await context?.close();
    server.close();
  }
}
(async()=>{
  const browser = await chromium.launch({headless:true});
  try {
    for (const [width,height] of [[1366,768],[390,844],[320,568],[1920,1080]]) {
      const context = await browser.newContext({viewport:{width,height},isMobile:width<500,hasTouch:width<500,deviceScaleFactor:1});
      const page = await context.newPage();
      page.on('pageerror',error=>errors.push(error.message));
      const size = width+'x'+height;
      for (const direction of ['a','b']) {
        for (const screen of ['home','solo','team']) {
          await go(page,direction,screen);
          await save(page,direction+'-'+screen+'-'+size);
        }
        if (width===390 || width===1366) {
          if (direction==='b') {
            await page.getByRole('link',{name:'Draft Bans & lineup'}).click();
            await page.getByRole('heading',{name:'Draft priorities'}).waitFor();
          } else if (width===390) {
            await page.getByRole('link',{name:/Draft tools/}).click();
          }
          if (direction==='a' && width===390) await page.locator('.draft-rail').evaluate(el=>el.scrollIntoView({block:'start'}));
          await save(page,direction+'-draft-'+size);
          await page.getByText('Build lineup',{exact:true}).click();
          assert.equal(await page.locator('.roster li').count(),5);
          if (width===390 || direction==='a') await page.locator('.lineup').evaluate(el=>el.scrollIntoView({block:'center'}));
          await save(page,direction+'-lineup-'+size);
        }
        if (width===390) {
          await go(page,direction,'solo');
          if (direction==='a') await page.getByRole('link',{name:'Recommended bans'}).click();
          else await page.getByRole('link',{name:'See recommended bans'}).click();
          await save(page,direction+'-solo-bans-'+size);
        }
      }
      if (width===1366 || width===390) {
        for (const [type,screens] of [['paired',['home','solo']],['current',['home','solo']]]) {
          for (const screen of screens) {
            await go(page,'a',screen,{type});
            await save(page,'a-type-'+type+'-'+screen+'-'+size);
          }
        }
      }
      if (width===390) {
        for (const screen of ['home','solo','team']) {
          await go(page,'a',screen);
          if (screen==='home') await page.getByRole('combobox',{name:'Region'}).selectOption('lan');
          await zoomText(page);
          await save(page,'a-text-200-'+screen+'-'+size);
          const target = screen === 'home' ? '.setup' : '.canonical';
          await page.locator(target).evaluate(el=>el.scrollIntoView({block:'start'}));
          await save(page,'a-text-200-'+screen+'-detail-'+size);
        }
        await go(page,'a','team');
        await page.getByRole('combobox',{name:'Sort by'}).selectOption('pick_rate');
        await page.getByRole('link',{name:'Camille (#1)'}).waitFor();
        assert.equal(await page.locator('.ranked-row h3').first().innerText(),'Renekton');
        assert.match(await page.locator('.ranked-row').first().innerText(),/Pick rate/);
        await save(page,'a-pick-rate-team-'+size);
        await page.getByRole('combobox',{name:'Difficulty'}).selectOption('easy');
        assert.equal(await page.locator('.canonical h3').innerText(),'Dr. Mundo');
        assert.match(await page.locator('.bans li').first().innerText(),/Camille/);
        await go(page,'b','solo');
        await page.getByRole('button',{name:/Akali/}).click();
        assert.equal(await page.getByRole('heading',{name:'Akali'}).count(),1);
        await save(page,'b-inspect-solo-'+size);
        await page.getByRole('button',{name:'Back to Darius'}).click();
        await page.getByRole('heading',{name:'Darius'}).waitFor();
        await go(page,'a','home');
        await page.keyboard.press('Tab');
        assert.equal(await page.evaluate(()=>document.activeElement.textContent.trim()), 'Skip to content');
        await page.getByRole('radio',{name:/Flex/}).check();
        await page.getByRole('button',{name:'View recommendations'}).focus();
        await save(page,'a-keyboard-home-'+size);
        await page.keyboard.press('Enter');
        await page.getByRole('heading',{name:'Flex / Clash', exact:true}).waitFor();
        await page.locator('a[href*="role=jungle"]').click();
        await page.getByRole('heading',{name:'Jarvan IV'}).waitFor();
        await page.locator('summary[aria-label="Evidence for Jarvan IV"]').focus();
        await page.keyboard.press('Enter');
        assert.equal(await page.locator('.canonical details').getAttribute('open'),'');
        await go(page,'a','home');
        await page.getByRole('combobox',{name:'Region'}).selectOption('lan');
        await page.getByRole('button',{name:'View recommendations'}).click();
        await page.getByRole('heading',{name:'This context has no prototype snapshot'}).waitFor();
      }
      await context.close();
    }
    const context = await browser.newContext({viewport:{width:844,height:390},reducedMotion:'reduce',hasTouch:true});
    const page = await context.newPage();
    for (const screen of ['home','solo','team']) {
      await go(page,'a',screen);
      await save(page,'a-landscape-'+screen+'-844x390');
    }
    await context.close();
    await nativeZoom();
    const review = await browser.newPage();
    await review.goto(pathToFileURL(path.join(base,'compare.html')).href);
    await review.getByRole('combobox',{name:'Screen'}).selectOption('draft');
    await review.getByRole('combobox',{name:'Viewport'}).selectOption('390x844');
    assert.equal(await review.locator('img').count(),2);
    await review.evaluate(()=>Promise.all([...document.images].map(img=>img.decode())));
    await review.getByRole('link',{name:'Open A · Ranked list prototype'}).click();
    await review.waitForFunction(()=>location.hash==='#draft-tools' && scrollY>0);
    await review.close();
    for (const [name, metric] of Object.entries(metrics)) {
      assert.equal(metric.doc[0],metric.viewport[0],name+' horizontal overflow');
      assert.deepEqual(metric.clipped,[],name+' clipped text');
    }
    assert.deepEqual(errors,[]);
    console.log('Rendered ' + Object.keys(metrics).length + ' screenshots. Interaction assertions passed.');
  } finally {
    fs.writeFileSync(path.join(base,'research','render-metrics.json'),JSON.stringify(metrics,null,2));
    await browser.close();
  }
})().catch(error=>{ console.error(error); process.exitCode=1; });
