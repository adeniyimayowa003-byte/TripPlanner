"""In-app conversation, with public FAQs and a fail-closed model integration."""
import time
from flask import Blueprint,abort,current_app,render_template,request

from assistant_answers import fallback_answer,catalog_source
from csrf import get_csrf_token,valid_csrf_token

blueprint=Blueprint('assistant',__name__)
_SAMPLES=('What does my allowance cover?','Why are meals missing?',
          'I cleared my cookies and lost my trips','Tell me about the Eiffel Tower')


@blueprint.before_request
def enabled():
    if not current_app.config.get('PHASE10_ASSISTANT_ENABLED') or not current_app.config.get('PHASE10_HELP_ENABLED'):
        abort(404)


@blueprint.after_request
def private_response(response):
    response.headers['Cache-Control']='private, no-store'
    response.headers['Referrer-Policy']='no-referrer'
    response.headers['X-Content-Type-Options']='nosniff'
    return response


@blueprint.route('/assistant',methods=['GET','POST'])
def conversation():
    deadline=time.monotonic()+15
    question=''
    answer=None
    error=''
    status=200
    runtime=current_app.extensions.get('assistant_runtime') if request.is_secure else None
    token=request.cookies.get('__Host-tripplanner_account','')
    model_ready=runtime is not None and runtime.principal(token) is not None
    if request.method=='POST':
        if not valid_csrf_token(request.form.get('csrf_token')):
            error='This form could not be verified. Reload the assistant and try again.'
            status=400
        else:
            question=request.form.get('question','').strip()
            if not question or len(question)>1000:
                error='Enter a question of 1–1,000 characters.'
                question=question[:1000]
                status=400
            else:
                notice='Live AI is unavailable. Using the approved FAQ fallback.' if request.form.get('use_model')=='on' else ''
                if request.form.get('use_model')=='on' and runtime is not None:
                    answer=runtime.answer(question,token=token,consent=request.form.get('consent')=='on',
                        trip_id=request.form.get('trip_id'),trip_consent=request.form.get('use_trip')=='on',deadline=deadline)
                else:answer=fallback_answer(question,notice)
    if model_ready and runtime.principal(token) is None:
        model_ready=False
        question=''  # Do not echo an old private turn after in-flight logout.
    options=runtime.options(token) if model_ready else ()
    return render_template('assistant.html',question=question,answer=answer,error=error,
                           samples=_SAMPLES,model_ready=model_ready,trip_options=options,
                           disclosure=runtime.disclosure if model_ready else None),status


@blueprint.get('/assistant/sources/<place_id>')
def source_page(place_id):
    from catalog import load_catalog
    try:place=next((p for p in load_catalog() if p['id']==place_id),None)
    except (OSError,ValueError):place=None
    if place is None:abort(404)
    return render_template('assistant_source.html',source=catalog_source(place),place=place)


@blueprint.get('/assistant/context/<trip_id>')
def selected_context(trip_id):
    runtime=current_app.extensions.get('assistant_runtime') if request.is_secure else None
    source=runtime.context_source(request.cookies.get('__Host-tripplanner_account',''),trip_id) if runtime else None
    if source is None:abort(404)
    return render_template('assistant_source.html',source=source,place=None)
