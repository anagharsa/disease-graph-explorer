def score_candidates(selected_ids, rows, profiles, limit=50):
    selected=set(selected_ids)
    ranked=[]
    for row in rows:
        matched=set(row["matched_ids"]) & selected
        documented=set(profiles.get(row["disease"]["id"], []))
        profile_count=int(row.get("profile_count",len(documented)))
        union_count=len(selected)+profile_count-len(matched)
        score=(len(matched)/union_count) if union_count else 0.0
        ranked.append({"disease":row["disease"],"score":round(score,4),"matched_ids":sorted(matched),"matched_names":row["matched_names"],"undocumented_ids":sorted(selected-matched),"matched_count":len(matched),"selected_count":len(selected),"disease_profile_count":profile_count})
    return sorted(ranked,key=lambda x:(-x["score"], x["disease"].get("name","")))[:limit]
