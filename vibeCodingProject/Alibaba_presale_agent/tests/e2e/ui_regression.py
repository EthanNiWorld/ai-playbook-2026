"""前端 UI 回归（CDP 驱动真实浏览器）
运行: .venv/bin/python tests/e2e/ui_regression.py [--mock]
前置: 8000 端口服务已就绪；默认真实调用 LLM，--mock 拦截问答与反馈请求。
--mock 不消耗模型额度、不写入问答数据库，可独立回归布局与流式交互。

覆盖：空态首屏 / 真实流式对话 / 消息与气泡样式 / 来源与价格徽章 /
思考折叠 / 反馈面板 hidden 显隐 / 价格表宽屏免横滑与窄屏横滑 /
表头不逐字折行 / 移动端断点 / 控制台零报错 / 首屏聚焦布局 /
侧栏收起 / 新会话状态 / 中文输入法 / 短视口与空态恢复

注意：默认模式会向 data/qa.db 写入 1 条回答 + 1 条点踩反馈（session 为本次随机 uuid），
验证后可自行清理。
"""

import argparse
import base64
import json
import subprocess
import sys
import time
from pathlib import Path
from urllib.request import urlopen

import httpx
from websockets.sync.client import connect

CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
CDP_PORT = 9333
APP = "http://127.0.0.1:8000/"
PROFILE = f"/tmp/apa-cdp-prof-{int(time.time())}"
PASS, FAIL = 0, 0

# 仅在测试浏览器中替换 fetch；数据为 UI 夹具，不代表真实模型报价。
MOCK_API = r"""
(() => {
  const originalFetch = window.fetch.bind(window);
  window.__uiRequests = [];
  window.__uiFeedback = [];
  window.__uiFailNext = false;
  window.fetch = async (url, init = {}) => {
    const path = new URL(url, location.href).pathname;
    if (path === '/api/feedback') {
      window.__uiFeedback.push(JSON.parse(init.body));
      return new Response('{}', {headers: {'Content-Type': 'application/json'}});
    }
    if (path !== '/api/chat') return originalFetch(url, init);
    window.__uiRequests.push(JSON.parse(init.body));
    if (window.__uiFailNext) {
      window.__uiFailNext = false;
      throw new TypeError('模拟连接中断');
    }
    const table = '## 测试价格表（仅用于 UI 回归）\n\n' +
      '| Region | 输入价格 (Input) | 缓存输入价格 (Cache Input) | 输出价格 (Output) | 显式缓存创建 (Cache Write) | 备注 |\n' +
      '| --- | --- | --- | --- | --- | --- |\n' +
      '| Singapore | $1.00 | $0.10 | $2.00 | — | 测试 |\n' +
      '| Beijing | $1.00 | $0.10 | $2.00 | — | 测试 |\n';
    const events = [
      {type: 'status', message: '正在核实测试来源…'},
      {type: 'sources', sources: [{kind: 'official', title: '测试定价来源', url: 'https://example.com/pricing'}]},
      {type: 'think', text: '这是模拟流式思考，用于检查折叠状态。'},
      {type: 'delta', text: table.slice(0, 80)},
      {type: 'delta', text: table.slice(80)},
      {type: 'done', answer_id: 1, price_status: 'official'},
    ];
    const encoder = new TextEncoder();
    return new Response(new ReadableStream({
      async start(controller) {
        for (const ev of events) {
          await new Promise(resolve => setTimeout(resolve, 150));
          controller.enqueue(encoder.encode('data: ' + JSON.stringify(ev) + '\n\n'));
        }
        controller.close();
      }
    }), {headers: {'Content-Type': 'text/event-stream'}});
  };
})();
"""


def check(name, cond, detail=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  OK   {name}")
    else:
        FAIL += 1
        print(f"  FAIL {name}   {detail}")


class CDP:
    def __init__(self, ws_url):
        self.ws = connect(ws_url, max_size=64 * 1024 * 1024)
        self._id = 0
        self.console = []

    def send(self, method, **params):
        self._id += 1
        mid = self._id
        self.ws.send(json.dumps({"id": mid, "method": method, "params": params}))
        while True:
            msg = json.loads(self.ws.recv())
            if msg.get("id") == mid:
                if "error" in msg:
                    raise RuntimeError(f"{method}: {msg['error']}")
                return msg.get("result", {})
            self._collect(msg)

    def _collect(self, msg):
        m = msg.get("method")
        if m == "Runtime.exceptionThrown":
            d = msg["params"]["exceptionDetails"]
            self.console.append("EXCEPTION " + str(d.get("text")) + " " +
                                str((d.get("exception") or {}).get("description", ""))[:200])
        elif m == "Runtime.consoleAPICalled":
            if msg["params"]["type"] in ("error", "warning"):
                parts = [str(a.get("value", a.get("description", "")))
                         for a in msg["params"]["args"]]
                self.console.append(msg["params"]["type"].upper() + " " + " ".join(parts)[:200])
        elif m == "Log.entryAdded":
            e = msg["params"]["entry"]
            if e.get("level") in ("error", "warning"):
                self.console.append(
                    e["level"].upper() + " " + str(e.get("text"))[:120]
                    + " @ " + str(e.get("url", ""))[:80])

    def ev(self, expr):
        r = self.send("Runtime.evaluate",
                      expression=expr, returnByValue=True, awaitPromise=True)
        if "exceptionDetails" in r:
            raise RuntimeError(str(r["exceptionDetails"])[:300])
        return r.get("result", {}).get("value")

    def shot(self, path):
        data = self.send("Page.captureScreenshot", format="png")["data"]
        Path(path).write_bytes(base64.b64decode(data))
        print(f"  📸 {path}")


def wait_devtools():
    for _ in range(40):
        try:
            tabs = json.loads(urlopen(f"http://127.0.0.1:{CDP_PORT}/json/list").read())
            for t in tabs:
                if t.get("type") == "page":
                    return t["webSocketDebuggerUrl"]
        except Exception:
            pass
        time.sleep(0.25)
    raise RuntimeError("DevTools 未就绪")


def main():
    parser = argparse.ArgumentParser(description="真实浏览器 UI 回归")
    parser.add_argument("--mock", action="store_true", help="拦截问答和反馈，不调用模型或写数据库")
    args = parser.parse_args()
    print("=" * 60)
    print("前端 UI 回归（真实页面 + " + ("模拟 SSE" if args.mock else "真实流式对话") + "）")
    print("=" * 60)

    try:
        httpx.get("http://127.0.0.1:8000/api/health", timeout=5).raise_for_status()
    except Exception as e:
        print(f"服务不可用: {e}")
        sys.exit(2)

    proc = subprocess.Popen(
        [CHROME, "--headless=new", "--disable-gpu", "--hide-scrollbars",
         "--no-first-run", "--no-default-browser-check",
         "--remote-allow-origins=*",
         f"--remote-debugging-port={CDP_PORT}", f"--user-data-dir={PROFILE}",
         "--window-size=1440,900", "about:blank"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        cdp = CDP(wait_devtools())
        cdp.send("Runtime.enable")
        cdp.send("Log.enable")
        cdp.send("Page.enable")
        cdp.send("Emulation.setDeviceMetricsOverride",
                 width=1440, height=900, deviceScaleFactor=1, mobile=False)
        if args.mock:
            cdp.send("Page.addScriptToEvaluateOnNewDocument", source=MOCK_API)
        cdp.send("Page.navigate", url=APP)
        time.sleep(2.5)

        # ── [1] 空态 ──
        print("\n[1] 空态首屏")
        st = cdp.ev("""(() => {
          const q = s => document.querySelector(s);
          const cs = (s, p) => q(s) ? getComputedStyle(q(s))[p] : null;
          return {
            chatClass: q('#chat').className,
            text: q('#chat').innerText.trim(),
            avatarDisplay: cs('.avatar', 'display'),
            sendW: q('#send').getBoundingClientRect().width,
            sendH: q('#send').getBoundingClientRect().height,
            sendBg: cs('#send', 'backgroundColor'),
            sendRadius: cs('#send', 'borderRadius'),
            sidebarDisplay: cs('.sidebar', 'display'),
            chips: document.querySelectorAll('.chip').length,
            userMsgs: document.querySelectorAll('.msg.user').length,
            composerRadius: cs('.composer', 'borderRadius'),
            headingSize: cs('.msg.welcome h1', 'fontSize'),
            newDisabled: q('#newSession').disabled && q('#newSessionTop').disabled,
            sendDisabled: q('#send').disabled,
            subtitleSize: cs('.brand-sub', 'fontSize'),
            welcomeBottom: q('.msg.welcome').getBoundingClientRect().bottom,
            composerTop: q('.composer').getBoundingClientRect().top,
            composerBottom: q('.composer').getBoundingClientRect().bottom,
            suggestionsTop: q('#suggestions').getBoundingClientRect().top,
            suggestionsBottom: q('#suggestions').getBoundingClientRect().bottom,
            docOverflow: document.documentElement.scrollWidth > window.innerWidth,
          };
        })()""")
        check("#chat 带 is-empty", "is-empty" in st["chatClass"], st["chatClass"])
        check("首屏标题已渲染为 h1 文本（无字面量 ###/**）",
              "今天想了解什么？" in st["text"] and "###" not in st["text"]
              and "**" not in st["text"], st["text"][:80])
        check("欢迎标题字号 36px", st["headingSize"] == "36px", st["headingSize"])
        check("品牌副标题 12px，弱于主标题", st["subtitleSize"] == "12px", st["subtitleSize"])
        check("空态两个新会话入口与发送按钮禁用", st["newDisabled"] and st["sendDisabled"])
        check("首屏欢迎语、输入框、推荐问题集中有序",
              0 <= st["composerTop"] - st["welcomeBottom"] < 60
              and st["composerBottom"] <= st["suggestionsTop"]
              and st["suggestionsBottom"] < 900, str(st))
        check("头像隐藏 display:none", st["avatarDisplay"] == "none", st["avatarDisplay"])
        check("发送按钮 40×40 / 13px 圆角 / 空态弱化",
              (st["sendW"], st["sendH"]) == (40.0, 40.0)
              and st["sendBg"] == "rgb(238, 236, 230)" and st["sendRadius"] == "13px",
              str((st["sendW"], st["sendH"], st["sendBg"], st["sendRadius"])))
        check("侧栏 1440 下可见", st["sidebarDisplay"] != "none", st["sidebarDisplay"])
        check("首屏 4 个推荐问题", st["chips"] == 4, st["chips"])
        check("空态无用户消息", st["userMsgs"] == 0, st["userMsgs"])
        check("composer 圆角 22px", st["composerRadius"] == "22px", st["composerRadius"])
        check("1440 下无横向溢出", st["docOverflow"] is False)

        # 背景层（实景虚化方案已于 2026-11-05 放弃回滚，现为纯白极简）
        bg = cdp.ev("""(() => {
          const q = s => document.querySelector(s);
          return {
            bodyBg: getComputedStyle(document.body).backgroundImage,
            overlay: getComputedStyle(document.body, '::before').backgroundColor,
            mainBg: getComputedStyle(q('.main')).backgroundColor,
            sidebarBg: getComputedStyle(q('.sidebar')).backgroundColor,
            sidebarBlur: getComputedStyle(q('.sidebar')).backdropFilter,
          };
        })()""")
        check("纯白极简：无背景图残留", not (bg["bodyBg"] or "").strip() or "none" == (bg["bodyBg"] or "none"), bg["bodyBg"][:60])
        check("纯白极简：侧栏无毛玻璃残留", "blur" not in (bg["sidebarBlur"] or ""), str(bg["sidebarBlur"]))
        print(f"  观察: 主区背景={bg['mainBg']} / body 白遮罩={bg['overlay']}")

        cdp.shot("/tmp/apa-reg-1-empty.png")

        cdp.ev("document.querySelector('#sidebarToggle').click()")
        check("桌面侧栏可收起，顶栏保留新会话入口", cdp.ev("""(() => {
          const q = s => document.querySelector(s);
          return getComputedStyle(q('#sidebar')).display === 'none'
            && q('#sidebarToggle').getAttribute('aria-expanded') === 'false'
            && getComputedStyle(q('#newSessionTop')).display !== 'none';
        })()"""))
        cdp.ev("document.querySelector('#sidebarToggle').click()")
        check("侧栏可重新展开", cdp.ev("document.querySelector('#sidebarToggle').getAttribute('aria-expanded') === 'true'"))
        cdp.ev("""(() => {
          const input = document.querySelector('#input');
          input.value = '输入法测试';
          input.dispatchEvent(new Event('input', {bubbles: true}));
          input.dispatchEvent(new KeyboardEvent('keydown', {key: 'Enter', isComposing: true, bubbles: true}));
          input.dispatchEvent(new KeyboardEvent('keydown', {key: 'Enter', shiftKey: true, bubbles: true}));
        })()""")
        check("中文组词确认与 Shift+Enter 不误发送", cdp.ev("!document.querySelector('.msg.user') && !document.querySelector('#send').disabled"))
        cdp.ev("document.querySelector('#input').value = ''; document.querySelector('#input').dispatchEvent(new Event('input'))")

        # ── [2] 真实对话：点第一个 chip ──
        print("\n[2] 点击示例问题 → 流式回答（最长等 180s）")
        cdp.ev("document.querySelectorAll('.chip')[0].click()")
        check("生成期间禁止新会话且推荐问题收起", cdp.ev("""(() => {
          const q = s => document.querySelector(s);
          return q('#newSession').disabled && q('#newSessionTop').disabled
            && q('#send').disabled && q('#suggestions').hidden
            && getComputedStyle(q('#suggestions')).display === 'none';
        })()"""))
        done = False
        for i in range(90):
            time.sleep(2)
            s = cdp.ev("""(() => {
              const bs = [...document.querySelectorAll('.msg.bot .bubble')];
              const last = bs[bs.length - 1];
              return {
                bots: bs.length,
                len: last ? last.textContent.length : 0,
                cursor: !!document.querySelector('.cursor'),
                table: !!document.querySelector('.bubble table'),
                statusHidden: document.querySelector('#statusBar').hidden,
              };
            })()""")
            if s["table"] and not s["cursor"] and s["statusHidden"]:
                done = True
                break
        check("流式回答已完成（表格出现 / 光标消失 / 状态条收起）", done, str(s))

        snap = cdp.ev("""(() => {
          const q = s => document.querySelector(s);
          const cs = (s, p) => q(s) ? getComputedStyle(q(s))[p] : null;
          const users = document.querySelectorAll('.msg.user');
          const ub = q('.msg.user .bubble');
          const bb = q('.msg.bot .bubble');
          const tb = q('.bubble table');
          const ths = [...document.querySelectorAll('.bubble th')].map(t => t.textContent);
          const tds = [...document.querySelectorAll('.bubble td')].map(t => t.textContent);
          return {
            chatClass: q('#chat').className,
            userCount: users.length,
            userBg: ub ? getComputedStyle(ub).backgroundColor : null,
            userRadius: ub ? getComputedStyle(ub).borderRadius : null,
            userAlignRight: ub ? Math.round(ub.getBoundingClientRect().right) : 0,
            botBg: bb ? getComputedStyle(bb).backgroundColor : null,
            botPadding: bb ? getComputedStyle(bb).paddingTop : null,
            sourcesHidden: q('.sources') ? q('.sources').hidden : null,
            sourceChips: [...document.querySelectorAll('.source-chip')]
              .map(a => a.className + '|' + a.textContent),
            priceBadge: q('.price-badge') ? q('.price-badge').textContent : null,
            thinkOpen: q('.think') ? q('.think').open : null,
            thinkMeta: q('.think-meta') ? q('.think-meta').textContent : null,
            feedbackHidden: q('.feedback') ? q('.feedback').hidden : null,
            panelHidden: q('.fb-panel') ? q('.fb-panel').hidden : null,
            tableThs: ths, tableRows: tds.length,
            tableFits: tb ? tb.scrollWidth <= tb.clientWidth + 1 : null,
            tableW: tb ? Math.round(tb.getBoundingClientRect().width) : 0,
            contentW: q('.msg.bot .bubble-wrap') ?
              Math.round(q('.msg.bot .bubble-wrap').getBoundingClientRect().width) : 0,
            bodyHasKbPath: /knowledge\\/|alibaba-ai-hub\\//.test(q('#chat').innerText),
            docOverflow: document.documentElement.scrollWidth > window.innerWidth,
          };
        })()""")
        check("对话态 is-empty 已移除", "is-empty" not in snap["chatClass"], snap["chatClass"])
        check("用户消息 1 条", snap["userCount"] == 1, snap["userCount"])
        check("用户气泡浅灰 #f4f4f4 / 圆角 20px",
              snap["userBg"] == "rgb(244, 244, 244)" and snap["userRadius"] == "20px",
              str((snap["userBg"], snap["userRadius"])))
        check("助手正文无气泡（背景透明 / padding 0）",
              snap["botBg"] in ("rgba(0, 0, 0, 0)", "transparent") and snap["botPadding"] == "0px",
              str((snap["botBg"], snap["botPadding"])))
        check("来源区可见且含官方证据", snap["sourcesHidden"] is False
              and any("official" in c for c in snap["sourceChips"]), str(snap["sourceChips"]))
        check("价格徽章已联网核实", (snap["priceBadge"] or "").startswith("✅"), snap["priceBadge"])
        check("思考面板存在且正文开始后已收起", snap["thinkOpen"] is False, snap["thinkOpen"])
        check("思考耗时文案已更新", "s" in (snap["thinkMeta"] or ""), snap["thinkMeta"])
        check("反馈按钮已显示", snap["feedbackHidden"] is False, snap["feedbackHidden"])
        check("反馈详情面板默认收起", snap["panelHidden"] is True, snap["panelHidden"])
        check("价格表已渲染且列齐",
              snap["tableRows"] > 0 and any("Region" in t for t in snap["tableThs"]),
              str(snap["tableThs"]))
        check("宽屏表格无需横滑（scrollWidth<=clientWidth）", snap["tableFits"] is True)
        check("助手内容列撑满 768", snap["contentW"] == 768, snap["contentW"])
        check("正文无知识库路径泄漏",
              snap["bodyHasKbPath"] is False)
        check("对话态无横向溢出", snap["docOverflow"] is False)
        check("回复完成后两个新会话入口恢复可用", cdp.ev("!document.querySelector('#newSession').disabled && !document.querySelector('#newSessionTop').disabled"))
        cdp.shot("/tmp/apa-reg-2-chat.png")

        # ── [3] 反馈面板 hidden 回归（历史 bug：display 覆盖 hidden）──
        print("\n[3] 点 👎 → 反馈面板显隐（hidden 关键回归）")
        cdp.ev("document.querySelector('.fb-down').click()")
        time.sleep(0.6)
        fb = cdp.ev("""(() => {
          const q = s => document.querySelector(s);
          const p = q('.fb-panel');
          return {
            hidden: p.hidden,
            display: getComputedStyle(p).display,
            reasons: document.querySelectorAll('.fb-reason').length,
            titleColor: getComputedStyle(q('.fb-title')).color,
            titleText: q('.fb-title').textContent,
            submitVisible: getComputedStyle(q('.fb-submit')).display,
          };
        })()""")
        check("面板展开（hidden=false 且 display=flex）",
              fb["hidden"] is False and fb["display"] == "flex", str((fb["hidden"], fb["display"])))
        check("5 个点踩原因按钮", fb["reasons"] == 5, fb["reasons"])
        check("面板标题已去红（非 #B91C1C）", fb["titleColor"] != "rgb(185, 28, 28)", fb["titleColor"])
        check("提交按钮可见", fb["submitVisible"] != "none", fb["submitVisible"])
        cdp.shot("/tmp/apa-reg-3-feedback.png")

        cdp.ev("document.querySelectorAll('.fb-reason')[0].click()")
        cdp.ev("document.querySelector('.fb-panel textarea').value = '回归测试反馈';")
        cdp.ev("document.querySelector('.fb-submit').click()")
        time.sleep(1.5)
        after = cdp.ev("""(() => {
          const q = s => document.querySelector(s);
          return {
            hidden: q('.fb-panel').hidden,
            display: getComputedStyle(q('.fb-panel')).display,
            note: q('.fb-note').textContent,
          };
        })()""")
        check("提交后面板收起（display 不再覆盖 hidden）",
              after["hidden"] is True and after["display"] == "none",
              str((after["hidden"], after["display"])))
        check("提交后提示已更新", "已记录" in after["note"], after["note"])

        # ── [4] 移动端断点 ──
        print("\n[4] 390×844 移动端断点")
        cdp.send("Emulation.setDeviceMetricsOverride",
                 width=390, height=844, deviceScaleFactor=2, mobile=True)
        time.sleep(1.2)
        m = cdp.ev("""(() => {
          const q = s => document.querySelector(s);
          const tb = q('.bubble table');
          const tbStyle = tb ? getComputedStyle(tb) : null;
          return {
            vw: window.innerWidth,
            sidebar: getComputedStyle(q('.sidebar')).display,
            docScroll: document.documentElement.scrollWidth,
            overflow: document.documentElement.scrollWidth > window.innerWidth,
            tableScroll: tb ? tb.scrollWidth > tb.clientWidth + 1 : null,
            tableDisplay: tbStyle ? tbStyle.display : null,
            tdNowrap: q('.bubble td') ? getComputedStyle(q('.bubble td')).whiteSpace : null,
            thNowrap: q('.bubble th') ? getComputedStyle(q('.bubble th')).whiteSpace : null,
            thRows: [...document.querySelectorAll('.bubble th')].map(t => {
              const cs = getComputedStyle(t);
              const lh = parseFloat(cs.lineHeight) || 19;
              // 减去上下 padding，否则 1 行也会算成 2 行
              const h = t.getBoundingClientRect().height
                - parseFloat(cs.paddingTop) - parseFloat(cs.paddingBottom);
              return Math.max(1, Math.round(h / lh));
            }),
            thTexts: [...document.querySelectorAll('.bubble th')].map(t => t.textContent),
            sendSize: q('#send').getBoundingClientRect().width,
            placeholder: q('#input').placeholder,
          };
        })()""")
        check("移动端侧栏隐藏", m["sidebar"] == "none", m["sidebar"])
        check("390 视口无横向溢出", m["overflow"] is False, f"scrollWidth={m['docScroll']}")
        check("窄屏价格表改为内部横滑", m["tableDisplay"] == "block" and m["tableScroll"] is True,
              str((m["tableDisplay"], m["tableScroll"])))
        check("单元格不折字（white-space nowrap）", m["tdNowrap"] == "nowrap", m["tdNowrap"])
        check("窄屏表头单行不逐字折行",
              m["thNowrap"] == "nowrap" and max(m["thRows"]) <= 1,
              str((m["thNowrap"], m["thRows"], m["thTexts"])))
        check("移动端 placeholder 不被裁切", len(m["placeholder"]) <= 10, m["placeholder"])
        check("移动端发送按钮触控尺寸 44px", m["sendSize"] == 44.0, m["sendSize"])
        check("移动端新会话入口可见且可用", cdp.ev("getComputedStyle(document.querySelector('#newSessionTop')).display !== 'none' && !document.querySelector('#newSessionTop').disabled"))
        cdp.shot("/tmp/apa-reg-4-mobile.png")

        # ── [5] 短视口、空态恢复与模拟异常 ──
        cdp.send("Emulation.setDeviceMetricsOverride",
                 width=390, height=420, deviceScaleFactor=1, mobile=True)
        check("短视口对话区仍可滚动，输入区未被裁切", cdp.ev("""(() => {
          const q = s => document.querySelector(s);
          const input = q('.composer').getBoundingClientRect();
          return q('#chat').clientHeight > 100 && input.top > 0 && input.bottom <= innerHeight;
        })()"""))
        cdp.ev("document.querySelector('#newSessionTop').click()")
        check("手机新会话恢复欢迎语、推荐问题与禁用状态", cdp.ev("""(() => {
          const q = s => document.querySelector(s);
          return q('#workspace').classList.contains('is-empty') && !!q('.msg.welcome h1')
            && !q('.msg.user') && !q('#suggestions').hidden
            && q('#newSession').disabled && q('#newSessionTop').disabled && q('#send').disabled;
        })()"""))
        for width, height in [(320, 568), (390, 844), (820, 700), (1024, 768)]:
            cdp.send("Emulation.setDeviceMetricsOverride",
                     width=width, height=height, deviceScaleFactor=1, mobile=width <= 820)
            check(f"空态 {width}×{height} 无横向溢出且输入框可达", cdp.ev("""(() => {
              const q = s => document.querySelector(s);
              q('#input').scrollIntoView({block: 'center'});
              const r = q('#input').getBoundingClientRect();
              return document.documentElement.scrollWidth <= innerWidth
                && r.top >= 0 && r.bottom <= innerHeight
                && [...document.querySelectorAll('.chip')].every(el => el.scrollWidth <= el.clientWidth);
            })()"""))
            if width == 390:
                cdp.shot("/tmp/apa-reg-5-mobile-empty.png")
        if args.mock:
            # ── [4.5] 截图附件（多模态入口，mock）──
            print("\n[4.5] 截图附件：入口 / 附件条 / 请求体（mock）")
            cdp.send("Emulation.clearDeviceMetricsOverride")
            time.sleep(0.5)
            shot_b64 = base64.b64encode(
                (Path(__file__).parent / "assets" / "apa_screenshot_sample.png").read_bytes()
            ).decode()
            cdp.ev(f"""(() => {{
              const bin = atob('{shot_b64}');
              const arr = new Uint8Array(bin.length);
              for (let i = 0; i < bin.length; i++) arr[i] = bin.charCodeAt(i);
              const file = new File([arr], 'shot.png', {{type: 'image/png'}});
              const dt = new DataTransfer();
              dt.items.add(file);
              const input = document.querySelector('#fileInput');
              input.files = dt.files;
              input.dispatchEvent(new Event('change', {{bubbles: true}}));
            }})()""")
            time.sleep(0.6)  # FileReader 异步
            check("📎 按钮存在且附件条渲染缩略图",
                  cdp.ev("""(() => {
                    const bar = document.querySelector('#attachBar');
                    return bar && !bar.hidden && bar.querySelectorAll('.attach-item img').length === 1
                      && !!document.querySelector('#attach');
                  })()"""))
            check("仅有附件无文本时发送按钮可点", cdp.ev("!document.querySelector('#send').disabled"))
            cdp.ev("""(() => {
              const input = document.querySelector('#input');
              input.value = '这张截图里的模型多少钱';
              input.dispatchEvent(new Event('input'));
              input.dispatchEvent(new KeyboardEvent('keydown', {key: 'Enter', bubbles: true}));
            })()""")
            time.sleep(2.2)  # mock SSE 全部事件约 1.2s，加上首帧
            check("请求体携带 images（data URL）",
                  cdp.ev("""(() => {
                    const req = window.__uiRequests.at(-1);
                    return req && req.images && req.images.length === 1
                      && req.images[0].startsWith('data:image/png;base64,');
                  })()"""))
            check("用户气泡展示截图缩略图",
                  cdp.ev("document.querySelectorAll('.msg.user .msg-images img').length === 1"))
            check("附件发送后附件条清空", cdp.ev("document.querySelector('#attachBar').hidden"))
            cdp.ev(f"""(() => {{
              // 追加第二张 → 验证移除按钮与纯图提交路径
              const bin = atob('{shot_b64}');
              const arr = new Uint8Array(bin.length);
              for (let i = 0; i < bin.length; i++) arr[i] = bin.charCodeAt(i);
              const dt = new DataTransfer();
              dt.items.add(new File([arr], 'shot2.png', {{type: 'image/png'}}));
              const input = document.querySelector('#fileInput');
              input.files = dt.files;
              input.dispatchEvent(new Event('change', {{bubbles: true}}));
            }})()""")
            time.sleep(0.6)
            cdp.ev("document.querySelector('.attach-remove').click()")
            time.sleep(0.2)
            check("移除按钮工作，附件条隐藏",
                  cdp.ev("document.querySelector('#attachBar').hidden"),
                  "移除后应隐藏")
            cdp.ev("document.querySelector('#newSession').click()")
            time.sleep(0.2)
            check("新会话同时清空待发附件",
                  cdp.ev("document.querySelector('#attachBar').hidden && document.querySelectorAll('.attach-item').length === 0"))

            cdp.ev("""(() => {
              window.__uiFailNext = true;
              const input = document.querySelector('#input');
              input.value = '模拟网络错误';
              input.dispatchEvent(new Event('input'));
              input.dispatchEvent(new KeyboardEvent('keydown', {key: 'Enter', bubbles: true}));
            })()""")
            time.sleep(0.3)
            check("异常后恢复操作，错误信息可见", cdp.ev("!!document.querySelector('.error-text') && !document.querySelector('#newSession').disabled && document.querySelector('#statusBar').hidden"))
            check("新会话请求不携带旧对话历史", cdp.ev("window.__uiRequests.at(-1).history.length === 0"))
            check("反馈走模拟接口且只提交一次", cdp.ev("window.__uiFeedback.length === 1"))
            cdp.ev("document.querySelector('#newSession').click()")
            check("桌面入口同样可重置失败对话", cdp.ev("!!document.querySelector('.msg.welcome') && !document.querySelector('.error-text')"))

        # ── [6] 控制台 ──
        print("\n[6] 控制台")
        time.sleep(0.5)
        errs = [c for c in cdp.console]
        check("控制台零 error/warning", len(errs) == 0, " | ".join(errs[:5]))

    finally:
        proc.terminate()
        proc.wait(timeout=10)

    print("-" * 60)
    print(f"结果: {PASS} 通过 / {FAIL} 失败")
    sys.exit(1 if FAIL else 0)


if __name__ == "__main__":
    main()
