export type Phenotype={id:string;name:string;definition?:string|null;synonyms?:string[]}
export type Disease={id:string;name:string;definition?:string|null;source?:string}
export type Candidate={disease:Disease;score:number;matched_ids:string[];matched_names:string[];undocumented_ids:string[];matched_count:number;selected_count:number;additional_phenotypes:Phenotype[]}
export type Stats={diseases:number;phenotypes:number;associations:number;sources:number;ontology_relationships:number;dataset:string}
export type GraphNode={id:string;name?:string;kind:string;[key:string]:any}
export type GraphEdge={source:string;target:string;type:string}
export type GraphData={nodes:GraphNode[];edges:GraphEdge[]}
