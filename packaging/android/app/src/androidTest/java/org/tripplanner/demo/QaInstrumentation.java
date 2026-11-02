package org.tripplanner.demo;

import android.app.Activity;
import android.app.Instrumentation;
import android.content.Intent;
import android.os.Bundle;
import android.view.View;
import android.view.ViewGroup;
import android.webkit.WebView;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.TimeUnit;
import org.json.JSONTokener;

/** Actual WebView journey in a separate test APK, never a production JS bridge. */
public final class QaInstrumentation extends Instrumentation {
    private Activity activity;
    private WebView web;
    private String last = "";
    private boolean resume;
    private String systemExpected;
    private volatile String externalMap;
    @Override public void onCreate(Bundle args) { super.onCreate(args); resume=args!=null && "true".equals(args.getString("resume")); systemExpected=args==null?null:args.getString("system"); start(); }
    private WebView find(View v) {
        if (v instanceof WebView) return (WebView)v;
        if (v instanceof ViewGroup) for(int i=0;i<((ViewGroup)v).getChildCount();i++) {
            WebView found=find(((ViewGroup)v).getChildAt(i)); if(found!=null)return found;
        }
        return null;
    }
    private String js(String script) throws Exception {
        CountDownLatch ready=new CountDownLatch(1);
        String[] result={"null"};
        runOnMainSync(() -> web.evaluateJavascript(script,value->{result[0]=value;ready.countDown();}));
        if(!ready.await(2,TimeUnit.SECONDS))throw new Exception("JavaScript callback timeout during navigation");
        Object decoded=new JSONTokener(result[0]).nextValue();
        return decoded.toString();
    }
    private void expect(String script,String expected) throws Exception {
        long end=System.currentTimeMillis()+15000;
        while(System.currentTimeMillis()<end) {
            try { last=js(script); if(last.contains(expected))return; }
            catch(Exception transientNavigation) {
                if(activity.isDestroyed() || activity.isFinishing())throw new Exception("The Activity closed during navigation",transientNavigation);
                last="The current document is still navigating";
            }
            Thread.sleep(150);
        }
        throw new Exception("Expected "+expected+". Last result: "+last.substring(0,Math.min(220,last.length())));
    }
    private void capture(String name) throws Exception {
        waitForIdleSync();Thread.sleep(250);
        android.graphics.Bitmap bitmap=getUiAutomation().takeScreenshot();
        try(java.io.FileOutputStream file=new java.io.FileOutputStream(new java.io.File(getTargetContext().getFilesDir(),name))) {
            bitmap.compress(android.graphics.Bitmap.CompressFormat.PNG,100,file);
        }
        bitmap.recycle();
    }
    private void tap(String selector) throws Exception {
        String selected="document.querySelector("+org.json.JSONObject.quote(selector)+")";
        js(selected+".scrollIntoView({block:'center',behavior:'instant'}); 'scrolled'");
        waitForIdleSync();Thread.sleep(250);
        expect("(function(){let r="+selected+".getBoundingClientRect();return String(r.top>=0&&r.bottom<=innerHeight&&r.left>=0&&r.right<=innerWidth);})()","true");
        org.json.JSONObject point=new org.json.JSONObject(js("(function(){let r="+selected+".getBoundingClientRect();return JSON.stringify({x:r.x+r.width/2,y:r.y+r.height/2});})()"));
        float[] xy=new float[2];
        runOnMainSync(()->{int[] at=new int[2];web.getLocationOnScreen(at);xy[0]=at[0]+web.getPaddingLeft()+(float)point.optDouble("x")*web.getScale();xy[1]=at[1]+web.getPaddingTop()+(float)point.optDouble("y")*web.getScale();android.util.Log.i("TripPlannerQA","tap "+selector+" rect="+point+" screen="+java.util.Arrays.toString(xy)+" scale="+web.getScale()+" size="+web.getWidth()+"x"+web.getHeight());});
        long time=android.os.SystemClock.uptimeMillis();
        sendPointerSync(android.view.MotionEvent.obtain(time,time,android.view.MotionEvent.ACTION_DOWN,xy[0],xy[1],0));
        sendPointerSync(android.view.MotionEvent.obtain(time,time+90,android.view.MotionEvent.ACTION_UP,xy[0],xy[1],0));
    }
    @Override public void onStart() {
        Bundle out=new Bundle();
        try {
            Intent launch=new Intent();launch.setClassName("org.tripplanner.demo","org.tripplanner.demo.MainActivity");
            launch.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
            activity=startActivitySync(launch);
            for(int i=0;i<100 && web==null;i++) {
                runOnMainSync(()->web=find(activity.getWindow().getDecorView()));Thread.sleep(100);
            }
            if(web==null)throw new Exception("No app WebView after startup");
            expect("document.body.innerText","Less searching");
            out.putString("launch","passed");
            capture("qa-home.png");
            if(systemExpected!=null) {
                js("(function(){let s=document.querySelector('#appearance');s.value='system';s.dispatchEvent(new Event('change',{bubbles:true}));return s.value;})()");
                expect("String(window.matchMedia('(prefers-color-scheme: dark)').matches)",systemExpected);
                if("true".equals(systemExpected)) {
                    js("(function(){let s=document.querySelector('#appearance');s.value='light';s.dispatchEvent(new Event('change',{bubbles:true}));return s.value;})()");
                    expect("getComputedStyle(document.documentElement).getPropertyValue('--page-bg').trim()","#faf9f3");
                    out.putString("manual_light_over_device_dark","passed");
                    js("(function(){let s=document.querySelector('#appearance');s.value='system';s.dispatchEvent(new Event('change',{bubbles:true}));return s.value;})()");
                }
                capture("qa-system-"+systemExpected+".png");
                out.putString("device_appearance","passed");
                out.putString("result","PASS");finish(Activity.RESULT_OK,out);return;
            }
            if(resume) {
                expect("document.querySelector('#appearance').value","dark");
                tap("a[href='/trips']");
                expect("location.pathname","/trips");
                expect("document.body.innerText","Android presentation QA");
                tap("a[href='/trips/1']");
                expect("document.body.innerText","135.00");
                out.putString("saved_trip_after_process_restart","passed");
                out.putString("dark_after_process_restart","passed");
                out.putString("result","PASS");
                finish(Activity.RESULT_OK,out);
                return;
            }
            tap("a[href='/plan']");
            expect("location.pathname","/plan");
            expect("!!document.querySelector('#trip-form')","true");
            js("(function(){let d=document.querySelector('#destination');d.value='Paris, France';d.dispatchEvent(new Event('change',{bubbles:true}));return d.value;})()");
            js("(function(){document.querySelector('#days').value='3';document.querySelector('#budget').value='300';document.querySelectorAll('input[name=interests]').forEach(e=>e.checked=['food','history'].includes(e.value));return 'filled';})()");
            tap("#trip-form button[type=submit]");
            expect("location.pathname","/recommendations");
            expect("document.body.innerText","Matches");
            out.putString("recommendations","passed");
            tap("a[href='/itinerary']");
            expect("location.pathname","/itinerary");
            expect("document.body.innerText","135.00");
            out.putString("itinerary_exact_estimate","passed");
            runOnMainSync(()->out.putString("back_history_available",String.valueOf(web.canGoBack())));
            sendKeyDownUpSync(android.view.KeyEvent.KEYCODE_BACK);
            waitForIdleSync();
            expect("location.pathname","/recommendations");
            out.putString("native_back","passed");
            tap("a[href='/itinerary']");
            expect("location.pathname","/itinerary");
            js("document.querySelector('#trip-name').value='Android presentation QA'; 'filled'");
            tap(".save-form button[type=submit]");
            expect("location.pathname","/trips/");
            expect("document.body.innerText","Android presentation QA");
            out.putString("save","passed");
            js("(function(){let s=document.querySelector('#appearance');s.value='dark';s.dispatchEvent(new Event('change',{bubbles:true}));return s.value;})()");
            expect("document.documentElement.getAttribute('data-appearance')","dark");
            java.io.File settings=new java.io.File(getTargetContext().getFilesDir(),"tripplanner/settings.json");
            boolean remembered=false;
            for(int i=0;i<60;i++) {
                if(new String(java.nio.file.Files.readAllBytes(settings.toPath()),java.nio.charset.StandardCharsets.UTF_8).contains("\"appearance\": \"dark\"")) { remembered=true;break; }
                Thread.sleep(100);
            }
            if(!remembered)throw new Exception("Native appearance settings did not persist");
            out.putString("dark_persistence_request","passed");
            expect("Array.from(document.images).filter(e=>e.complete&&e.naturalWidth>0).length>0","true");
            out.putString("local_photos","passed");
            out.putString("saved_path",js("location.pathname"));
            addMonitor(new ActivityMonitor() {
                @Override public ActivityResult onStartActivity(Intent intent) {
                    if(Intent.ACTION_VIEW.equals(intent.getAction())) {
                        externalMap=intent.getDataString();return new ActivityResult(Activity.RESULT_OK,null);
                    }
                    return null;
                }
            });
            tap("a[href^='https://www.google.com/maps/']");
            for(int i=0;i<70 && externalMap==null;i++)Thread.sleep(100);
            if(externalMap==null || !externalMap.contains("api=1") || !externalMap.contains("Luxembourg"))throw new Exception("Maps did not route to an external venue intent");
            out.putString("external_maps_intent","passed");
            expect("location.pathname","/trips/");
            js("window.scrollTo(0,0); 'top'");capture("qa-saved-dark.png");
            out.putString("result","PASS");
            finish(Activity.RESULT_OK,out);
        } catch(Exception error) {
            try { capture("qa-failure.png"); } catch(Exception ignored) { }
            out.putString("result","FAIL: "+error.toString());
            android.util.Log.e("TripPlannerQA","Journey failed",error);
            finish(Activity.RESULT_CANCELED,out);
        }
    }
}
