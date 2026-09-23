import re

with open(r"C:\Users\shrut\OneDrive\Documents\Google Photo\stitch_dashboard\code.html", "r", encoding="utf-8") as f:
    html = f.read()

# 1. Update KPIs
html = html.replace(">4,850<", ">{{ total_raw }}<")
html = html.replace(">Play Store: 2.1k • AppStore: 1.8k • Reddit: 950<", ">Live data from connected sources<")
html = html.replace(">2,714<", ">{{ total_filtered }}<")
html = html.replace(">2,136 non-search reviews removed (-44%)<", ">{{ total_raw - total_filtered }} non-search reviews removed<")
html = html.replace(">56.0%<", '>{% if total_raw > 0 %}{{ "%.1f"|format(total_filtered / total_raw * 100) }}{% else %}0{% endif %}%<')
html = html.replace('>Exact Date Search<', ' title="{{ clusters[0][\'primary_failure_mode\'] if clusters else \'\' }}">{{ clusters[0][\'label\'] if clusters else \'N/A\' }}<')
# Clean up duplicate title tag from previous replace
html = html.replace('title="Exact Date & Timestamp Search Failure" title="', 'title="')
html = html.replace(">\n              98\n            <", ">\n              {{ clusters[0]['opportunity_score'] if clusters else '0' }}\n            <")
html = html.replace(">Impact Score: 98/100 (342 reports)<", ">Impact Score: {{ clusters[0]['opportunity_score'] if clusters else '0' }}/100 ({{ clusters[0]['doc_count'] if clusters else '0' }} reports)<")

# 2. Update Clusters Grid (Lines 237-330 approx)
# We will replace the entire grid with a jinja loop.
clusters_start = html.find('<!-- Break Reason 1 -->')
clusters_end = html.find('</section>', clusters_start)

jinja_clusters = """
          {% for cluster in clusters %}
          <div class="bg-surface-container-lowest rounded-2xl p-5 border {% if loop.index == 1 %}border-2 border-primary/40 shadow-sm{% else %}border-outline-variant/30 shadow-xs{% endif %} flex flex-col justify-between relative overflow-hidden group hover:shadow-md transition-all">
            <div class="absolute top-0 left-0 right-0 {% if loop.index == 1 %}h-1.5 bg-primary{% else %}h-1 bg-secondary{% endif %}"></div>
            <div>
              <div class="flex items-center justify-between mb-3">
                <span class="w-7 h-7 rounded-full {% if loop.index == 1 %}bg-primary-container text-on-primary{% else %}bg-surface-container-high text-on-surface{% endif %} font-bold text-xs flex items-center justify-center">#{{ loop.index }}</span>
                <span class="px-2 py-0.5 rounded-full {% if loop.index == 1 %}bg-error-container text-on-error-container{% else %}bg-secondary-fixed text-on-secondary-fixed{% endif %} font-label-sm text-label-sm font-bold">{% if cluster.severity_score > 80 %}Critical{% else %}High{% endif %}</span>
              </div>
              <h3 class="font-title-sm text-title-sm font-bold text-on-surface leading-snug">{{ cluster.label }}</h3>
              <p class="font-body-sm text-body-sm text-on-surface-variant mt-2 leading-relaxed">
                {{ cluster.summary }}
              </p>
            </div>
            <div class="mt-4 pt-3 border-t border-outline-variant/30 flex flex-col gap-1">
              <div class="flex items-center justify-between text-xs">
                <span class="text-on-surface-variant font-medium">Impact Score:</span>
                <span class="font-bold {% if loop.index == 1 %}text-primary{% else %}text-secondary{% endif %}">{{ cluster.opportunity_score }} / 100</span>
              </div>
              <div class="flex items-center justify-between text-xs">
                <span class="text-on-surface-variant font-medium">Volume:</span>
                <span class="font-semibold text-on-surface">{{ cluster.doc_count }} reviews</span>
              </div>
            </div>
          </div>
          {% endfor %}
        </div>
"""
# find the closing div of the grid
grid_end = html.rfind('</div>', clusters_start, clusters_end) + 6
html = html[:clusters_start] + jinja_clusters + html[grid_end:]


# 3. Update Raw Reviews Grid
reviews_start = html.find('<!-- Card 1 -->')
reviews_end = html.find('</section>', reviews_start)

jinja_reviews = """
          {% for review in reviews %}
          <div class="review-card bg-surface-container-lowest rounded-2xl p-5 border border-outline-variant/30 flex flex-col justify-between gap-3 shadow-xs hover:border-primary/40 transition-all" data-category="{{ review.source | lower }}">
            <div class="flex flex-col gap-2">
              <div class="flex items-center justify-between">
                <div class="flex items-center gap-1 text-amber-500">
                  <span class="material-symbols-outlined text-[18px]">star</span>
                  <span class="font-label-sm text-label-sm font-bold text-on-surface">{{ review.rating }}</span>
                </div>
                <span class="px-2 py-0.5 rounded-full bg-secondary-fixed text-on-secondary-fixed font-label-sm text-label-sm font-semibold">{{ review.source }}</span>
              </div>
              <p class="font-body-sm text-body-sm text-on-surface italic leading-relaxed">
                "{{ review.text }}"
              </p>
            </div>
            <div class="pt-3 border-t border-outline-variant/20 flex items-center justify-between text-xs text-on-surface-variant">
              <span class="font-medium">{{ review.date.strftime('%Y-%m-%d') if review.date else 'Unknown' }}</span>
              <span class="px-2 py-0.5 rounded bg-surface-container-high font-semibold">Raw Data</span>
            </div>
          </div>
          {% endfor %}
        </div>
"""
grid_end2 = html.rfind('</div>', reviews_start, reviews_end) + 6
html = html[:reviews_start] + jinja_reviews + html[grid_end2:]


with open(r"C:\Users\shrut\OneDrive\Documents\Google Photo\stitch_dashboard\code.html", "w", encoding="utf-8") as f:
    f.write(html)

print("Injected Jinja templates successfully.")
