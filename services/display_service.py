"""
Display service handling target resolution, runtime state, and display actions.
"""

from datetime import datetime
import display
from .storage import (
    PORT,
    ALLOWED_EXTENSIONS,
    load_slideshow_config,
    save_slideshow_config
)

# Global runtime state tracker
display_state = {
    "status": "idle",       # "running", "blank", "idle"
    "mode": "default",      # "website", "image", "slideshow", "default", "mixed"
    "monitor": "both",
    "updated_at": datetime.now().isoformat(),
    "last_message": "Ready"
}

def get_viewer_url(monitor='both', mode='random', interval=30, fit=None):
    """Generate the local slideshow viewer URL for kiosk display"""
    clean_mode = mode if mode in ['random', 'sequential'] else 'random'
    url = f"http://127.0.0.1:{PORT}/viewer?monitor={monitor}&mode={clean_mode}&interval={interval}"
    if fit:
        url += f"&fit={fit}"
    return url

def _resolve_target(item, monitor_id='1', default_params=None):
    """Resolve display target (website, single image, slideshow, default) to a URL"""
    default_params = default_params or {}
    fit = default_params.get('fit', '')
    if isinstance(item, dict):
        t = item.get('type', 'website')
        if t == 'website':
            return item.get('url', item.get('value', '')) or ''
        elif t == 'image':
            img = item.get('image', item.get('value', ''))
            item_fit = item.get('fit', fit)
            fit_param = f"&fit={item_fit}" if item_fit else ""
            return f"http://127.0.0.1:{PORT}/viewer?single={img}&monitor={monitor_id}{fit_param}" if img else ""
        elif t == 'slideshow':
            mode = item.get('mode', default_params.get('slideshow_mode', default_params.get('mode', 'random')))
            if mode == 'slideshow' or mode not in ['random', 'sequential']:
                mode = default_params.get('slideshow_mode') or load_slideshow_config().get('mode', 'random')
            if mode not in ['random', 'sequential']:
                mode = 'random'
            interval = item.get('interval', default_params.get('interval', 30))
            item_fit = item.get('fit', fit)
            return get_viewer_url(monitor_id, mode, interval, item_fit)
        elif t == 'default':
            return ""
        return item.get('value', '')

    if not item:
        return ""
    if item == 'slideshow':
        mode = default_params.get('slideshow_mode', default_params.get('mode', 'random'))
        if mode == 'slideshow' or mode not in ['random', 'sequential']:
            mode = default_params.get('slideshow_mode') or load_slideshow_config().get('mode', 'random')
        if mode not in ['random', 'sequential']:
            mode = 'random'
        interval = default_params.get('interval', 30)
        return get_viewer_url(monitor_id, mode, interval, fit)
    if item.startswith('http://') or item.startswith('https://') or item.startswith('file://'):
        return item
    if any(item.lower().endswith('.' + ext) for ext in ALLOWED_EXTENSIONS):
        fit_param = f"&fit={fit}" if fit else ""
        return f"http://127.0.0.1:{PORT}/viewer?single={item}&monitor={monitor_id}{fit_param}"
    return item

def trigger_display_action(action_type, params=None):
    """Unified internal handler for triggering display state changes with dual-monitor mixing"""
    params = params or {}
    global display_state

    if action_type == "blank":
        success, res = display.blank_screen()
        if success:
            display_state.update({
                "status": "blank",
                "mode": "blank",
                "updated_at": datetime.now().isoformat(),
                "last_message": "Display blanked (screen turned off)"
            })
            return True, "Display blanked successfully"
        return False, f"Failed to blank display: {res}"

    elif action_type == "wake":
        success, res = display.wake_screen()
        if success:
            display_state.update({
                "status": "running",
                "mode": "default",
                "updated_at": datetime.now().isoformat(),
                "last_message": "Display woken up"
            })
            return True, "Display woken successfully"
        return False, f"Failed to wake display: {res}"

    # Handle display routing (website, image, slideshow, dual mix)
    monitor = params.get('monitor', 'both')
    
    # Save slideshow config if options provided
    if action_type == 'slideshow' or params.get('slideshow_mode') or params.get('interval') or params.get('fit'):
        cfg = load_slideshow_config()
        if params.get('slideshow_mode') in ['random', 'sequential']:
            cfg['mode'] = params['slideshow_mode']
        elif params.get('mode') in ['random', 'sequential']:
            cfg['mode'] = params['mode']
        if 'interval' in params:
            try:
                cfg['interval'] = int(params['interval'])
            except (ValueError, TypeError):
                pass
        if 'selected_images' in params and isinstance(params['selected_images'], list):
            cfg['selected_images'] = params['selected_images']
        if 'fit' in params and params['fit'] in ['contain', 'cover']:
            cfg['fit'] = params['fit']
        save_slideshow_config(cfg)

    # Check if monitor 1 and monitor 2 targets are specified explicitly
    target1_raw = params.get('monitor1') or params.get('target1')
    target2_raw = params.get('monitor2') or params.get('target2')

    if not target1_raw:
        if action_type == 'slideshow':
            target1_raw = 'slideshow'
        elif 'image1' in params or action_type == 'image':
            target1_raw = {'type': 'image', 'image': params.get('image1', ''), 'fit': params.get('fit', '')}
        else:
            target1_raw = {'type': 'website', 'url': params.get('url1', params.get('url', ''))}

    if not target2_raw:
        if action_type == 'slideshow':
            target2_raw = 'slideshow'
        elif 'image2' in params and params.get('image2'):
            target2_raw = {'type': 'image', 'image': params.get('image2', ''), 'fit': params.get('fit', '')}
        elif 'url2' in params and params.get('url2') is not None:
            target2_raw = {'type': 'website', 'url': params.get('url2', '')}
        else:
            target2_raw = target1_raw

    url1 = _resolve_target(target1_raw, '1', params)
    url2 = _resolve_target(target2_raw, '2', params)

    if monitor == '1':
        msg = "Updated Monitor 1"
    elif monitor == '2':
        msg = "Updated Monitor 2"
    else:
        msg = "Updated both monitors with selected configuration"

    success, res = display.start_display(url1=url1, url2=url2, monitor=monitor)
    if success:
        display_state.update({
            "status": "running",
            "mode": action_type if action_type in ['slideshow', 'website', 'image'] else 'mixed',
            "monitor": monitor,
            "updated_at": datetime.now().isoformat(),
            "last_message": msg
        })
        return True, msg
    return False, f"Failed to start display: {res}"
