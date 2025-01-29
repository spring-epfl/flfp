#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import json
import sys
import time

# import threading
import os
import traceback

from pyvirtualdisplay import Display
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

vdisplay: "Display"


def is_loaded(webdriver):
    """Check if the page is fully loaded."""
    return webdriver.execute_script("return document.readyState") == "complete"


def wait_until_loaded(webdriver, timeout=60, period=0.25, min_time=0):
    """Wait until the page is fully loaded or the timeout is reached."""
    start_time = time.time()
    mustend = time.time() + timeout
    while time.time() < mustend:
        if is_loaded(webdriver):
            if time.time() - start_time < min_time:
                time.sleep(min_time + start_time - time.time())
            return True
        time.sleep(period)
    return False


def image_alt_stats(driver):
    """Get the image alt stats."""

    script = """
    // get the count of images with an alt attribute where the :before is styled with background-image
    var images = document.querySelectorAll('img[alt]:not([alt=""])');
    var matches = []
    for (var i = 0; i < images.length; i++) {
        var image = images[i];
        var style = window.getComputedStyle(image, ':before');
        if (style.getPropertyValue('background') !== 'none' || style.getPropertyValue('background-image') !== 'none') {
            matches.push({
                'src': image.src, 
                'alt': image.alt,
                'style': {
                    'background': style.getPropertyValue('background')? style.getPropertyValue('background'): style.getPropertyValue('background-image'),
                }
            })
        }
    }
    return {
        'count': {
            'total': images.length,
            'withAlt': document.querySelectorAll('img[alt]:not([alt=""])').length,
            'matches': matches.length
        },
        'matches': matches
    }
    """

    return driver.execute_script(script)


def api_override(driver):
    """Override the postMessage and addEventListener functions to log messages."""

    # override postMessage to log messages

    script = """
    
    //on window ready add this
    (function() {
        
        if (window.POST_MESSAGE_LOG) return;
        
        window.POST_MESSAGE_LOG = [];
        window.LISTEN_MESSAGE_LOG = [];
        var originalPostMessage = window.postMessage;
        var patchedPostMessage = function(message, targetOrigin=undefined, transfer=undefined, options=undefined) {
            
            originalPostMessage(message, targetOrigin, transfer, options);
            
            window.POST_MESSAGE_LOG.push({
                'callstack': (new Error()).stack,
                'targetOrigin': targetOrigin? targetOrigin: options? options.origin? `${options.origin}`: '*': '*',
            });
        };
        window.postMessage = patchedPostMessage;
        
        window.addEventListener('message', function(event) {
            window.LISTEN_MESSAGE_LOG.push({
                'origin': `${event.origin}`,
                'source': `${event.source}`,
            });
        });
    })();
    """

    return driver.execute_script(script)


def iframe_and_post_message_stats(driver):
    """Get the iframe and postMessage stats."""

    script = """
    
    var iframes = [];
    
    try{
    document.querySelectorAll('iframe').forEach(function(iframe) {
        iframes.push({
            'src': iframe.src,
            'name': iframe.name,
            'title': iframe.title,
            'allow': iframe.allow,
            'loading': iframe.loading,
            'referrerPolicy': iframe.referrerPolicy
            });
    });
    }
    catch (e) {
        throw new Error(e + ' ' + e.stack);
    }
    
    var postMessageLog = window.POST_MESSAGE_LOG;
    var listenMessageLog = window.LISTEN_MESSAGE_LOG;
    
    // check if scripts contain the keyword `postMessage`
    
    var staticPostMessageCount = 0;
    
    document.querySelectorAll('script').forEach(function(script) {
        if (script.text.includes('window.postMessage')) {
            staticPostMessageCount += 1;
        }
    });
    
    return {
        'count': {
            'iframes': iframes.length,
            'postMessage': postMessageLog?.length,
            'listenMessage': listenMessageLog?.length,
            'staticPostMessage': staticPostMessageCount,
        },
        
        'iframes': iframes,
        'postMessage': postMessageLog,
        'listenMessage': listenMessageLog,
    }
    """

    return driver.execute_script(script)


def lazy_loading_stats(driver):
    """Get the lazy loading attack-related statistics."""

    script = """
    var images = document.querySelectorAll('img');
    var lazyImages = Array.prototype.filter.call(images, function(image) {
        return image.getAttribute('loading') === 'lazy';
    });
    
    return {
        'count': {
            'total': images.length,
            'lazy': lazyImages.length,
        },
        'lazy': lazyImages.map(function(image) {
            return {
                'src': image.src,
                'loading': image.loading,
            }
        })
    }
    """

    return driver.execute_script(script)


def container_style_queries(driver):
    """Get css styles where @container is used."""

    # external stylesheets
    script = """
    var stylesheets = document.styleSheets;
    var containerStyles = [];
    for (var i = 0; i < stylesheets.length; i++) {
        
        try{
        
        var rules = stylesheets[i].cssRules;
        for (var j = 0; j < rules.length; j++) {
            var rule = rules[j];
            if (rule.cssText.includes('@container')) {
                containerStyles.push({
                    'cssTextStart': rule.cssText.slice(0, 100),
                    'hasStyle': rule.cssText.includes('style('),
                })
            }
        }

        } catch (e) {
            console.log(e);
            }
    }
    return containerStyles;
    """

    return driver.execute_script(script)


def keyframes_with_background(driver):
    """Get the keyframes containing background-image styles."""

    # get keyframes with background-image

    script = """
    var stylesheets = document.styleSheets;
    var keyframes = [];
    for (var i = 0; i < stylesheets.length; i++) {
        
        try{
        
        var rules = stylesheets[i].cssRules;
        for (var j = 0; j < rules.length; j++) {
            var rule = rules[j];
            if (rule.type === 7) {
                keyframes.push({
                    'name': rule.name,
                    'cssText': rule.cssText,
                    'hasBackgroundImage': rule.cssText.includes('background-image') || rule.cssText.includes('background: url('),
                    'hasBackground': rule.cssText.includes('background'),
                    'makesRequest': rule.cssText.includes(' url('),
                })
            }
        }

        } catch (e) {
            console.log(e);
            }
    }
    return keyframes;
    """

    return driver.execute_script(script)


def main(number_of_tries, flag, args_lst):

    # Start X
    # vdisplay = Display(visible=False, size=(1920, 1080))

    # cpu = int(args_lst[2])

    # port = 5907 + cpu
    # vdisplay = Display(visible=True, size=(1920, 1080), backend='xvnc', rfbport=port)

    # vdisplay.start()

    # Prepare Chrome
    options = Options()
    # options.headless = False
    # options.add_argument("--headless=new")
    options.add_argument("no-sandbox")
    options.add_argument("--disable-animations")
    options.add_argument("--disable-web-animations")
    # options.add_argument("--single-process")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-cache")
    options.add_argument("--disable-features=IsolateOrigins,site-per-process")
    options.add_argument("--disable-features=AudioServiceOutOfProcess")
    options.add_argument(
        "user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Safari/537.36"
    )
    # options.add_extension("/home/seluser/measure/harexporttrigger-0.6.3.crx")
    options.binary_location = "/usr/local/bin/chrome/chrome"

    # Install other addons

    try:
        print(args_lst)
        fname = "/data/" + args_lst[0].split("//")[1] + "/stats.json"

        if os.path.exists(fname) and os.path.getsize(fname) > 0:
            print(f"{args_lst[0]} already crawled. Skipping...")
            return

        stat_data = {}

        # make sure the directory exists
        os.makedirs("/data/" + args_lst[0].split("//")[1], exist_ok=True)

        # Launch Chrome and install our extension for getting HARs
        driver = webdriver.Chrome(options=options)
        driver.set_page_load_timeout(args_lst[1])

        driver.get(args_lst[0])
        time.sleep(2)
        api_override(driver)
        wait_until_loaded(driver, args_lst[1])

        time.sleep(10)

        stat_data["image_alt"] = image_alt_stats(driver)
        stat_data["iframe_post_message"] = iframe_and_post_message_stats(driver)
        stat_data["lazy_loading"] = lazy_loading_stats(driver)
        stat_data["container_style"] = container_style_queries(driver)
        stat_data["animation"] = keyframes_with_background(driver)

        print("-" * 25)
        print(fname)
        print("-" * 25)

        f = open(fname, "w")
        json_obj = json.dumps(stat_data)
        f.write(json_obj)
        f.close()

    except Exception as e:
        print(e, "SITE: ", args_lst[0])
        print(traceback.format_exc())
        if number_of_tries == 0:
            vdisplay.stop()
            sys.exit(1)
        else:
            driver.quit()
            # vdisplay.stop()
            return main(number_of_tries - 1, flag, args_lst)

    driver.quit()
    # vdisplay.stop()

    time.sleep(3)


if __name__ == "__main__":
    # Parse the command line arguments
    parser = argparse.ArgumentParser()
    parser.add_argument("--websites", nargs="+")
    parser.add_argument("--timeout", type=int, default=60)
    # parser.add_argument('--extensions')
    parser.add_argument("--extensions-wait", type=int, default=10)
    parser.add_argument("--cpu", type=int)
    args = parser.parse_args()

    port = 5907 + args.cpu
    vdisplay = Display(visible=False, size=(1920, 1080))

    vdisplay.start()

    for website in args.websites:

        args_lst = [website, args.timeout, args.cpu]

        main(3, 0, args_lst)

    vdisplay.stop()
