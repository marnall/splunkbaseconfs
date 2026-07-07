#!/usr/bin/env python

import glob, os, shutil, datetime, filecmp, sys

dt = datetime.datetime.today()

def log(level, msg, output):
    print('%s level="%s" msg="%s" output="%s"' % (dt.isoformat(), level, msg, output) )
        
def main():
    
    defaultPath = 'default', 'data', 'ui', 'nav'
    localPath = 'local', 'data', 'ui', 'nav'
    
    sentryDefaultPath = os.path.abspath(os.path.join(sys.path[0], '..', *defaultPath))
    sentryDefaultNav = os.path.join(sentryDefaultPath, 'default.xml')
    log('INFO', 'Sentry default nav path', sentryDefaultNav)
    sentryLocalPath = os.path.abspath(os.path.join(sys.path[0], '..', *localPath))
    sentryLocalNav = os.path.join(sentryLocalPath, 'default.xml')
    log('INFO', 'Sentry local nav path', sentryLocalNav)

    
    # Check if local path and nav exists within sentry
    if not os.path.exists(sentryLocalNav):
        log('WARN', 'Sentry local nav missing', sentryLocalNav)

        log('INFO', 'Making nav directory', sentryLocalPath)
        os.makedirs(sentryLocalPath, mode=0775)
        
        log('INFO', 'Copying Sentry default nav to Sentry local nav', '%s -> %s' % (sentryDefaultNav, sentryLocalNav))
        shutil.copyfile(sentryDefaultNav, sentryLocalNav)
        
         
    sentryApps = [app for app in glob.glob(os.path.abspath(os.path.join(sys.path[0], '..', '..', 'sentry*'))) if os.path.exists(os.path.join(app, 'sentry_do_not_remove.txt'))]


    for dir in sentryApps:
        appLocalPath = os.path.abspath(os.path.join(dir, *localPath))
        appLocalNav = os.path.join(appLocalPath, 'default.xml')
        log('INFO', 'App local nav path', appLocalNav)
        
        if not os.path.exists(appLocalPath):
            log('WARN', 'App local path missing', appLocalPath)
            
            log('INFO', 'Making nav directory', appLocalPath)
            os.makedirs(appLocalPath, mode=0775)
            
            log('INFO', 'Copying Sentry local nav to App local nav', '%s -> %s' % (sentryLocalNav, appLocalNav))
            shutil.copyfile(sentryLocalNav, appLocalNav)
        
        if not os.path.exists(appLocalNav) or not filecmp.cmp(sentryLocalNav, appLocalNav):
            log('WARN', 'App local nav out of sync', appLocalNav)
            
            log('INFO', 'Copying Sentry local nav to App local nav', '%s -> %s' % (sentryLocalNav, appLocalNav))
            shutil.copyfile(sentryLocalNav, appLocalNav)


if __name__ == '__main__':
    try:
        main()
    except (KeyboardInterrupt):
        print("^C")
        exit()