#include "FoAGraphToolsLibrary.h"

#include "BlueprintEditorModule.h"
#include "BlueprintModes/WidgetBlueprintApplicationModes.h"
#include "Containers/Ticker.h"
#include "EdGraph/EdGraph.h"
#include "EdGraphUtilities.h"
#include "Editor.h"
#include "Engine/Blueprint.h"
#include "Engine/TextureRenderTarget2D.h"
#include "Framework/Docking/TabManager.h"
#include "GraphEditor.h"
#include "HAL/FileManager.h"
#include "HAL/PlatformTime.h"
#include "ImageUtils.h"
#include "Kismet2/BlueprintEditorUtils.h"
#include "Kismet2/KismetEditorUtilities.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Modules/ModuleManager.h"
#include "RenderingThread.h"
#include "Slate/WidgetRenderer.h"
#include "Subsystems/AssetEditorSubsystem.h"
#include "TextureResource.h"
#include "UObject/StrongObjectPtr.h"
#include "Widgets/Docking/SDockTab.h"

IMPLEMENT_MODULE(FDefaultModuleImpl, FoAGraphTools)
DEFINE_LOG_CATEGORY_STATIC(LogFoAGraphTools, Log, All);

namespace FoAGraphTools
{
// An Error-level script message becomes a RuntimeError in Python (PyUtil::InvokeFunctionCall); elsewhere it is logged.
static void Fail(const FString& Message)
{
	FFrame::KismetExecutionMessage(*(TEXT("FoAGraphTools: ") + Message), ELogVerbosity::Error);
}

static UEdGraph* FindGraph(UBlueprint* Blueprint, FName GraphName)
{
	TArray<UEdGraph*> Graphs;
	Blueprint->GetAllGraphs(Graphs);
	FString Names;
	for (UEdGraph* Graph : Graphs)
	{
		if (Graph && Graph->GetFName() == GraphName)
		{
			return Graph;
		}
		Names += (Names.IsEmpty() ? TEXT("") : TEXT(", ")) + GetNameSafe(Graph);
	}
	Fail(FString::Printf(TEXT("%s has no graph '%s'. It has: %s"), *Blueprint->GetName(), *GraphName.ToString(), *Names));
	return nullptr;
}

// First SGraphEditor under Widget that shows GraphName (any graph when None). Only foreground tabs are in the tree.
static TSharedPtr<SGraphEditor> FindGraphEditor(const TSharedRef<SWidget>& Widget, FName GraphName)
{
	static const FName GraphEditorType(TEXT("SGraphEditor"));
	if (Widget->GetType() == GraphEditorType)
	{
		TSharedRef<SGraphEditor> Editor = StaticCastSharedRef<SGraphEditor>(Widget);
		const UEdGraph* Graph = Editor->GetCurrentGraph();
		const bool bMatch = Graph && (GraphName.IsNone() || Graph->GetFName() == GraphName);
		return bMatch ? TSharedPtr<SGraphEditor>(Editor) : TSharedPtr<SGraphEditor>();
	}
	FChildren* Children = Widget->GetChildren();
	for (int32 Index = 0; Children && Index < Children->Num(); ++Index)
	{
		if (TSharedPtr<SGraphEditor> Found = FindGraphEditor(Children->GetChildAt(Index), GraphName))
		{
			return Found;
		}
	}
	return nullptr;
}

// One in-flight capture. It renders a private SGraphEditor on the same UEdGraph off-screen, so the editor's own widget
// is never reparented (FWidgetRenderer::DrawWidget would do that), and the image is not limited to the tab's size.
struct FCapture
{
	TStrongObjectPtr<UEdGraph> Graph; // a material editor's graph lives on a transient copy that dies when its editor closes
	TWeakPtr<SGraphEditor> LiveEditor;
	TSharedPtr<SGraphEditor> Editor;
	TSharedPtr<FWidgetRenderer> Renderer;
	TStrongObjectPtr<UTextureRenderTarget2D> Target;
	FVector2D Size = FVector2D(1920, 1080);
	FString Path;
	bool bZoomToFit = true;
	int32 Frame = 0;
	double ViewSetAt = 0;

	bool Tick(float DeltaTime)
	{
		if (!IsValid(Graph.Get()))
		{
			UE_LOG(LogFoAGraphTools, Error, TEXT("CaptureGraphPng: the graph was deleted before %s was written"), *Path);
			return false;
		}
		// After 3 draws the node widgets exist and are measured. Frame before drawing, so the last draw and the
		// readback agree on the target size. The current-view mode keeps following the live editor, which may still
		// be animating its own zoom.
		if (Frame == 3 || (Frame > 3 && !bZoomToFit))
		{
			FrameView();
			ViewSetAt = Frame == 3 ? FPlatformTime::Seconds() : ViewSetAt;
		}
		Renderer->DrawWidget(Target.Get(), Editor.ToSharedRef(), Size, DeltaTime);
		// A new panel shows its "Zoom 1:1" label bright and dims it to a faint resting state over ~1.25 s of real time.
		if (++Frame <= 3 || FPlatformTime::Seconds() - ViewSetAt < 1.5)
		{
			return true;
		}
		Save();
		return false;
	}

	void FrameView()
	{
		FVector2f Location;
		float Zoom = 1.f;
		if (!bZoomToFit)
		{
			if (TSharedPtr<SGraphEditor> Live = LiveEditor.Pin())
			{
				Live->GetViewLocation(Location, Zoom);
				Editor->SetViewLocation(Location, Zoom);
				const FVector2D LiveSize = Live->GetTickSpaceGeometry().GetLocalSize();
				Size = LiveSize.X >= 64 && LiveSize.Y >= 64 ? LiveSize : Size;
			}
		}
		else
		{
			FSlateRect Bounds(0, 0, 0, 0);
			bool bAny = false;
			for (UEdGraphNode* Node : Graph->Nodes)
			{
				FSlateRect NodeBounds;
				if (Node && Editor->GetBoundsForNode(Node, NodeBounds, 0.f))
				{
					Bounds = bAny ? Bounds.Expand(NodeBounds) : NodeBounds;
					bAny = true;
				}
			}
			constexpr float Margin = 64.f;
			constexpr float MaxPixels = 6144.f;
			const FVector2f Extent(Bounds.Right - Bounds.Left + 2 * Margin, Bounds.Bottom - Bounds.Top + 2 * Margin);
			Editor->SetViewLocation(FVector2f(Bounds.Left - Margin, Bounds.Top - Margin),
				FMath::Min3(1.f, MaxPixels / Extent.X, MaxPixels / Extent.Y));
			Editor->GetViewLocation(Location, Zoom); // the zoom snaps to the nearest zoom level
			Size = FVector2D(FMath::Clamp(Extent.X * Zoom, 640.f, 16384.f), FMath::Clamp(Extent.Y * Zoom, 360.f, 16384.f));
		}
		Target->ResizeTarget(FMath::CeilToInt(Size.X), FMath::CeilToInt(Size.Y));
	}

	void Save()
	{
		FlushRenderingCommands();
		const int32 Width = Target->SizeX;
		const int32 Height = Target->SizeY;
		TArray<FColor> Pixels;
		FTextureRenderTargetResource* Resource = Target->GameThread_GetRenderTargetResource();
		if (!Resource || !Resource->ReadPixels(Pixels) || Pixels.Num() != Width * Height)
		{
			UE_LOG(LogFoAGraphTools, Error, TEXT("CaptureGraphPng: pixel readback failed for %s"), *Path);
			return;
		}
		for (FColor& Pixel : Pixels)
		{
			Pixel.A = 255; // Slate leaves alpha 0 wherever it drew nothing
		}
		TArray64<uint8> Png;
		FImageUtils::PNGCompressImageArray(Width, Height, Pixels, Png);
		// Write, then rename, so a caller polling for the file never reads half a PNG.
		const FString Temp = Path + TEXT(".tmp");
		if (FFileHelper::SaveArrayToFile(Png, *Temp) && IFileManager::Get().Move(*Path, *Temp))
		{
			UE_LOG(LogFoAGraphTools, Log, TEXT("CaptureGraphPng: wrote %s (%dx%d)"), *Path, Width, Height);
		}
		else
		{
			UE_LOG(LogFoAGraphTools, Error, TEXT("CaptureGraphPng: could not write %s"), *Path);
		}
	}
};
}

void UFoAGraphToolsLibrary::CaptureGraphPng(UObject* Asset, FName GraphName, const FString& PngPath, bool bZoomToFit)
{
	using namespace FoAGraphTools;
	if (!Asset || PngPath.IsEmpty())
	{
		return Fail(TEXT("CaptureGraphPng needs an Asset and a PngPath"));
	}
	UAssetEditorSubsystem* AssetEditors = GEditor->GetEditorSubsystem<UAssetEditorSubsystem>();
	if (!AssetEditors->OpenEditorForAsset(Asset))
	{
		return Fail(FString::Printf(TEXT("could not open an editor for %s"), *Asset->GetPathName()));
	}

	UEdGraph* Graph = nullptr;
	TSharedPtr<SGraphEditor> Live;
	if (UBlueprint* Blueprint = Cast<UBlueprint>(Asset))
	{
		Graph = FindGraph(Blueprint, GraphName);
		if (!Graph)
		{
			return;
		}
		if (TSharedPtr<IBlueprintEditor> BlueprintEditor = FKismetEditorUtilities::GetIBlueprintEditorForObject(Blueprint, false))
		{
			if (BlueprintEditor->GetCurrentMode() == FWidgetBlueprintApplicationModes::DesignerMode)
			{
				BlueprintEditor->SetCurrentMode(FWidgetBlueprintApplicationModes::GraphMode);
			}
			Live = BlueprintEditor->OpenGraphAndBringToFront(Graph);
		}
	}
	else if (IAssetEditorInstance* Instance = AssetEditors->FindEditorForAsset(Asset, true))
	{
		// Material editors edit a transient copy, so their graph is only reachable through the editor's widgets.
		const TSharedPtr<FTabManager> Tabs = Instance->GetAssociatedTabManager();
		const TSharedPtr<SDockTab> Tab = Tabs.IsValid() ? Tabs->GetOwnerTab() : TSharedPtr<SDockTab>();
		if (Tab.IsValid())
		{
			Live = FindGraphEditor(Tab->GetContent(), GraphName);
			Live = Live.IsValid() ? Live : FindGraphEditor(Tab->GetContent(), NAME_None);
		}
		Graph = Live.IsValid() ? Live->GetCurrentGraph() : nullptr;
	}
	if (!Graph)
	{
		return Fail(FString::Printf(TEXT("found no graph editor for %s"), *Asset->GetPathName()));
	}
	if (Live.IsValid() && bZoomToFit)
	{
		Live->ZoomToFit(false); // so whoever watches the editor sees the whole graph too
	}

	const FString Path = FPaths::ConvertRelativePathToFull(PngPath);
	IFileManager::Get().Delete(*Path); // callers poll for the file, so never leave an older image there
	IFileManager::Get().MakeDirectory(*FPaths::GetPath(Path), true);

	TSharedRef<FCapture> Capture = MakeShared<FCapture>();
	Capture->Graph.Reset(Graph);
	Capture->LiveEditor = Live;
	Capture->Path = Path;
	Capture->bZoomToFit = bZoomToFit;
	Capture->Editor = SNew(SGraphEditor).GraphToEdit(Graph).IsEditable(false).ShowGraphStateOverlay(false);
	Capture->Editor->SetViewLocation(FVector2f::ZeroVector, 1.f); // cancels the animated zoom-to-fit a new panel starts with
	Capture->Renderer = MakeShared<FWidgetRenderer>(/*bUseGammaCorrection=*/true); // without it every colour comes out dark
	Capture->Renderer->SetIsPrepassNeeded(true);
	Capture->Target.Reset(FWidgetRenderer::CreateTargetFor(Capture->Size, TF_Bilinear, true));
	FTSTicker::GetCoreTicker().AddTicker(TEXT("FoAGraphCapture"), 0.f, [Capture](float DeltaTime) { return Capture->Tick(DeltaTime); });
}

FString UFoAGraphToolsLibrary::ExportNodesText(UBlueprint* Blueprint, FName GraphName)
{
	using namespace FoAGraphTools;
	if (!Blueprint)
	{
		Fail(TEXT("ExportNodesText needs a Blueprint"));
		return FString();
	}
	UEdGraph* Graph = FindGraph(Blueprint, GraphName);
	if (!Graph)
	{
		return FString();
	}
	TSet<UObject*> Nodes;
	for (UEdGraphNode* Node : Graph->Nodes)
	{
		if (Node)
		{
			Node->PrepareForCopying(); // as FBlueprintEditor::CopySelectedNodes does before exporting
			Nodes.Add(Node);
		}
	}
	FString Text;
	FEdGraphUtilities::ExportNodesToText(Nodes, Text);
	return Text;
}
