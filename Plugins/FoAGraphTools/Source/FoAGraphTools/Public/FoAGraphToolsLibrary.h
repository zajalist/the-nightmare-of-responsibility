#pragma once

#include "Kismet/BlueprintFunctionLibrary.h"
#include "FoAGraphToolsLibrary.generated.h"

class UBlueprint;

/** Graph helpers that editor Python lacks. Python: unreal.FoAGraphToolsLibrary.capture_graph_png / export_nodes_text. */
UCLASS()
class UFoAGraphToolsLibrary : public UBlueprintFunctionLibrary
{
	GENERATED_BODY()

public:
	/**
	 * Opens Asset's editor with GraphName in front, then renders the graph off-screen to PngPath about 1.5 s later.
	 * bZoomToFit: the whole graph at 1:1 (scaled down only past 6144 px); otherwise the editor's current view.
	 * Returns at once, so poll for the file. An old file at PngPath is deleted first. Works for Blueprints,
	 * Widget Blueprints (switched to Graph mode) and Materials/Material Functions (GraphName may be None there).
	 */
	UFUNCTION(BlueprintCallable, Category = "FoA|GraphTools")
	static void CaptureGraphPng(UObject* Asset, FName GraphName, const FString& PngPath, bool bZoomToFit = true);

	/** T3D of every node in a Blueprint graph, exactly what Ctrl+C in that graph would copy. */
	UFUNCTION(BlueprintCallable, Category = "FoA|GraphTools")
	static FString ExportNodesText(UBlueprint* Blueprint, FName GraphName);
};
