require.config({"paths":{"settings":"/static/app/getwatchlist/js/settings.js?v=41a79c760cb94799fd5c","react-dom":"/static/app/getwatchlist/js/react-dom.js?v=0316bb9fe8871c426983","react":"/static/app/getwatchlist/js/react.js?v=302f2a1255d084a04f21"},"shim":{"settings":{"exports":["settings"]},"react-dom":{"exports":"react-dom"},"react":{"exports":"react"}}});
                require([
                        "splunkjs/ready!",
                        "splunkjs/mvc/simplexml/ready!",
                        "splunkjs/mvc/utils",
                        "settings", "react-dom", "react"
                    ], function (mvc,
                                 ignored,
                                 splunkjsUtils,
                                 settings, reactdom, react
                    ) {
                        let default_tokens = mvc.Components.get("default"), submitted_tokens = mvc.Components.get("submitted");
                        let splunk_theme_name = window.__splunk_page_theme__ ? window.__splunk_page_theme__ : window.DASHBOARD_THEME ? window.DASHBOARD_THEME : "default";
                        let myObjects = $("#root").each((k, v)=>{
                            const root = reactdom.createRoot(
                                v, 
                                {identifierPrefix: "settings"});
                            const react_app = react.createElement(settings.default, {
                                    splunkjs: mvc,
                                    mvc: mvc,
                                    utils: splunkjsUtils,
                                    app_context: "getwatchlist",
                                    family: splunk_theme_name,
                                    color_scheme: splunk_theme_name,
                                    ...$(v).data(),
                                    default_tokens, submitted_tokens,
                                    
                                    });
                            
                            root.render(react_app);
                          }); //end iterator
                       });
                